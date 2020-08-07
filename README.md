Wow is it surprisingly tricky to do user uploaded files (typically photos)
these days. Unlike the old days, you can't just store user uploaded files
directly on your web server any more. Our servers are in the cloud and are
liable to disapear at a moment's notice. So now you need a separate permanent
file storage service.

The obvious choice is Amazon's S3.

djaveS3 has a bunch of useful stuff for getting the Django web framework,
browsers, Heroku hosting, and Amazon S3 cloud file storage all working
together.

There are two basic use cases when it comes to Amazon S3 buckets. You may want
random people on the internet to be able to see those files. In this case you
want all links to the files to bypass your server entirely and just go straight
to S3, so you're html will look like

    <h1>This photo is viewable by anybody!</h1>
    <img src="http://amazon.com/blahblahblah">

The other case is when users upload sensitive stuff like photos of their IDs or
credit cards or something. In that case, you want it to be impossible to view
photos directly on Amazon. You want to be able to put arbitrary security checks
in front of the bytes of these files. Your html will look like

    <h1>Only Steve can see this photo</h1>
    <img src="http://your-server.com/blahblahblah">

You may have as many buckets of either type as you want.

Now, it's easy for users to upload photos and then just abandon the page
they're on, so you end up with photos on your S3 that are utterly unreachable
and useless. So it's good to clean up after that stuff. Same for resizing
photos.

# An example

settings.py

    from djaveS3.bucket_config import BucketConfig

    BUCKETS = [BucketConfig(
        'steves-public-bucket', steves-iam-user-access-key-id,
        steves-iam-user-secret-access-key, is_public=False)]

models.py

    from datetime import date
    from django.db import models
    from django.utils.timezone import now
    from djaveS3.models.photo import Photo
    from djaveS3.models.bucket import get_bucket_config

    class StevePhoto(Photo):
      """ Photos only of Steve :D """
      how_old_is_steve_in_this_photo = models.PositiveIntegerField(
          help_text='In years')

      def explain_why_can_delete(self):
        if self.photo_age_in_years() > 10.0:
          return 'You can delete any photo of Steve that is over 10 years old'

      def calc_and_set_keep(self):
        years_until_I_can_delete = 10 - self.photo_age_in_years(self)
        fudge_factor = 10
        self.keep_until = now() + timedelta(
            days=years_until_I_can_delete * 365 + fudge_factor)

      def photo_age_in_years(self):
        steves_birthday = date(1990, 5, 14)
        photo_taken_ago = now().date() - steves_birthday
        photo_taken_years_ago = (photo_taken_ago.days) / 365
        photo_age = photo_taken_years_ago + self.how_old_is_steve_in_this_photo
        return photo_age

      def bucket_config(self):
        return get_bucket_config('steves-public-bucket')

clock.py  # Or whatever you use for cron

    from djaveS3.models.clean_up_files import (
        clean_up_never_used, clean_up_no_longer_needed)
    from djaveS3.models.photo import resize_all

    @cron(days=1)
    def clean_up_photos():
      clean_up_never_used()
      clean_up_no_longer_needed()
      # This is just a catch-all for when client side resizing and on-demand
      # server side resizing fail.
      resize_all()

# S3 Configuration

Brace yourself, S3 configuration has quite the learning curve. There are
not one, not two, but five places you have to configure permissions correctly
in order for this to work. If you have anything wrong, you're liable to get 403
forbidden errors when you try to do anything, but these 403 errors contain no
information. Good luck! :D

It all starts with the AWS console at https://us-east-2.console.aws.amazon.com
The two important services are S3 and IAm.

Type S3 in the services box. Find or create a bucket.  Now, when it comes to
websites being allowed to do things to files in an S3 bucket, click on the
bucket -> Permissions -> CORS configuration. Yep, it's a text file, an XML file
to be exact, and you have to configure domains and verbs. In order for users to
upload photos directly to Amazon S3, they'll need to be able to POST:

    <?xml version="1.0" encoding="UTF-8"?>
    <CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <CORSRule>
        <AllowedOrigin>*</AllowedOrigin>
        <AllowedMethod>POST</AllowedMethod>
        <AllowedHeader>*</AllowedHeader>
    </CORSRule>
    </CORSConfiguration>

Now, I could have sworn I uploaded publically readable files without this here
paragraph before. When you presign a post, you get to specify ACLs. I'll get to
that in a bit. So I THOUGHT I was just setting those to allow public read. But,
that no longer works. So when I made a s3_bucket_name policy that allowed public read,
I could finally reliably public read. Amazon S3 -> your s3_bucket_name -> permissions
-> Bucket Policy, and then here's an example of how to set it up so anybody can
read anything from the s3_bucket_name:

https://docs.aws.amazon.com/AmazonS3/latest/dev/example-s3_bucket_name-policies.html#example-s3_bucket_name-policies-use-case-2

    {
      "Version":"2012-10-17",
      "Statement":[
        {
          "Sid":"PublicRead",
          "Effect":"Allow",
          "Principal": "*",
          "Action":["s3:GetObject"],
          "Resource":["arn:aws:s3:::examplebucket/*"]
        }
      ]
    }

There's a set of particularly confusingly explained security settings on the
s3_bucket_name level. At least these are just checkboxes. s3_bucket_name ->
Permissions -> Block public access. If you want your files to be publically
visible, the only policy you can leave on, I believe, is "Block public access
to buckets and objects granted through new public s3_bucket_name policies." But
if you're getting 403s you may need to fuss with this too.  Honestly I really
don't understand these.

But that's not the whole picture, not by a long shot. The public can't just
upload whatever it wants with a simple post now, no no. Each upload has to
get signed by somebody with permission to the s3_bucket_name. If THAT isn't set up
correctly, you'll STILL get 403 forbidden errors.

Head back to the main console but this time type iam in the find services box.
Create or select an IAm user. Click in and check out the permissions tab. This
user will need a permission policy, which you can click on. This policy is
ANOTHER text file, this time in json! (I hate inconsistency. Isn't
inconsistency the best?) This time we have ACLs. I no longer know what that stands for, I'm sure it's very fancy, but basically, like, "user can verb."
Careful, it's tricky because you need some ACLs for the objects in the s3_bucket_name,
which is what arn:aws:s3:::my-bucket/* refers to, and some ACLs on
the s3_bucket_name itself, arn:aws:s3:::my-bucket. If you're missing ANY ACL
you'll get, you guessed it, 403 forbidden explanation-less errors. Or you could
just give it blanket permissions.

Here's a blanket permission example

Policy ARN arn:aws:iam::aws:policy/AmazonS3FullAccess

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": "*"
            }
        ]
    }

Here's a more targetted example

    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "Stmt1531852957000",
          "Effect": "Allow",
          "Action": [
            "s3:*"
          ],
          "Resource": [
            "arn:aws:s3:::my-bucket"
          ]
        }
      ]
    }


OK IAm users have credentials including a secret access key, and an access key
id. That's what gets configured in your settings file in those BucketConfig
objects I mentioned earlier.

Now, I logged in as publics3@hihoward.com, who is therefore a root user. You
CAN give your root user keys, but you don't want to. The reason I created an
IAm user instead of just using my root account keys is, the risk of what
happens if the keys are stolen. The IAm user has very limited permissions, so
if its keys are stolen, pretty much all you could do would be, like, delete our
images or something. Not the end of the world. If my root user's keys existed
and got stolen, that's root access, and the hacker could sign up for and use
services.

Aaaaand there's one more thing to consider. When you sign the metadata for a
file so it can upload to S3, you specify what the ACL ought to be for that
file. That is, permissions are also set on the object level, and that can
block, say, the public's ability to read the file. I think.

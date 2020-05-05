You need to configure your buckets in local_settings.py like so

from djaveS3.s3_bucket_config import S3BucketConfig

BUCKETS = [
    S3BucketConfig(
        'my-public-bucket', an_s3_access_key_id, an_s3_secret_access_key,
        is_public=True)]

boto3 does the heavy lifting of actually communicating with
Brace yourself, S3 configuration has quite the learning curve. There are
not one, not two, but five places you have to configure permissions correctly
in order for this to work. If you have anything wrong, you're liable to get 403
forbidden errors when you try to do anything, but these 403 errors contain no
information. Good luck! :D

It all starts with the AWS console at https://us-east-2.console.aws.amazon.com
The two important services are S3 and IAm.

Type S3 in the services box. Find or create a s3_bucket_name.
Now, when it comes to websites being allowed to do things to files in an S3
s3_bucket_name, click on the s3_bucket_name -> Permissions -> CORS configuration. Yep, it's a
text file, an XML file to be exact, and you have to configure domains and
verbs.

Now, I could have sworn I uploaded publically readable files without this here
paragraph before. When you presign a post, you get to specify ACLs. I'll get to
that in a bit. So I THOUGHT I was just setting those to allow public read. But,
that no longer works. So when I made a s3_bucket_name policy that allowed public read,
I could finally reliably public read. Amazon S3 -> your s3_bucket_name -> permissions
-> s3_bucket_name policy, and then here's an example of how to set it up so anybody can
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

There's one more set of particularly confusingly explained security settings on
the s3_bucket_name level. At least these are just checkboxes.  s3_bucket_name -> Permissions ->
Block public access. If you want your files to be publically visible, the only
policy you can leave on, I believe, is "Block public access to buckets and
objects granted through new public s3_bucket_name policies." But if you're getting 403s
you may need to fuss with this too.  Honestly I really don't understand these.

But that's not the whole picture, not by a long shot. The public can't just
upload whatever it wants with a simple post now, no no. Each upload has to
get signed by somebody with permission to the s3_bucket_name. If THAT isn't set up
correctly, you'll STILL get 403 forbidden errors.

Head back to the main console but this time type iam in the find services box.
Create or select an IAm user. Click in and check out the permissions tab. This
user will need a permission policy, which you can click on. This policy is
ANOTHER text file, this time in json! (I hate inconsistency. Isn't
inconsistency the best?) This time we have ACLs which stands for Access c???
list? Anyway, they're basically verbs. You also say what the user can verb.
Careful, it's tricky because you need some ACLs for the objects in the s3_bucket_name,
which is what arn:aws:s3:::prod-hihoward-public/* refers to, and some ACLs on
the s3_bucket_name itself, arn:aws:s3:::prod-hihoward-public. If you're missing ANY ACL
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
        "arn:aws:s3:::stayd-id-verification-dev"
      ]
    }
  ]
}


OK IAm users have credentials including a secret access key, and an access
key id. You can see these being used in use in this file as
settings.S3_ACCESS_KEY_ID_SENSITIVE and S3_SECRET_ACCESS_KEY_SENSITIVE

Now, I logged in as publics3@hihoward.com, who is therefore a root user. You
CAN give your root user keys, but you don't want to. The reason I created an
IAm user instead of just giving publics3@hihoward.com keys is, the risk of
what happens if the keys are stolen. The IAm user has very limited permissions,
so if its keys are stolen, pretty much all you could do would be, like, delete
our images or something. Not the end of the world. If publics3@hihoward.com's
keys existed and got stolen, that's root access, and the hacker could sign up
for and use services.

Aaaaand there's one more thing to consider. When you sign the metadata for a
file so it can upload to S3, you specify what the ACL ought to be for that
file. That is, permissions are also set on the object level, and that can
block, say, the public's ability to read the file. I think.

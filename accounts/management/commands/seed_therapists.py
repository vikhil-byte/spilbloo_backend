import os
from django.core.management.base import BaseCommand
from django.conf import settings
from accounts.models import User
from core.s3_utils import upload_to_s3

class Command(BaseCommand):
    help = 'Uploads dummy.png to S3 and updates all therapist profiles in the database'

    def handle(self, *args, **options):
        # Ensure bucket exists and has public read policy
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
        if bucket_name:
            from core.s3_utils import get_s3_client
            import json
            s3 = get_s3_client()
            
            try:
                region = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
                if region and region != 'us-east-1':
                    s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                else:
                    s3.create_bucket(Bucket=bucket_name)
                self.stdout.write(f"Created S3 bucket '{bucket_name}'.")
            except Exception as e:
                self.stdout.write(f"Bucket creation failed or skipped: {e}")

            try:
                # Put public-read policy
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/*"
                    }]
                }
                s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
                self.stdout.write("Configured bucket with public read-only policy.")
            except Exception as e:
                self.stdout.write(f"Bucket policy setup failed: {e}")



        # 1. Upload dummy.png to S3
        dummy_path = os.path.join(settings.BASE_DIR, 'dummy.png')
        if os.path.exists(dummy_path):
            self.stdout.write("Uploading dummy.png to S3...")
            with open(dummy_path, 'rb') as f:
                class DummyFile:
                    def __init__(self, file_obj):
                        self.file = file_obj
                        self.content_type = 'image/png'
                    def read(self, *args, **kwargs):
                        return self.file.read(*args, **kwargs)
                    def seek(self, *args, **kwargs):
                        return self.file.seek(*args, **kwargs)

                s3_key = upload_to_s3(DummyFile(f), 'dummy.png')
                if s3_key:
                    self.stdout.write(self.style.SUCCESS("Successfully uploaded dummy.png to S3!"))
                else:
                    self.stdout.write(self.style.ERROR("Failed to upload dummy.png to S3. Check S3 settings."))
        else:
            self.stdout.write(self.style.WARNING(f"dummy.png not found at {dummy_path}"))

        # 2. Update all therapists (role_id = 5)
        therapists = User.objects.filter(role_id=5)
        count = 0
        for t in therapists:
            t.profile_file = 'dummy.png'
            t.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {count} therapists with dummy.png in the database."))

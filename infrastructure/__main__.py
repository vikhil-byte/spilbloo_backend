import pulumi
import pulumi_aws as aws

# Configuration
config = pulumi.Config()
instance_type = config.get("instanceType") or "t4g.micro"
ebs_volume_size = config.get_int("volumeSize") or 10
key_name = config.get("keyName") # Set via: pulumi config set keyName <your-key-name>

# 1. Network: Use Default VPC
vpc = aws.ec2.get_vpc(default=True)
subnets = aws.ec2.get_subnets(filters=[aws.ec2.GetSubnetsFilterArgs(
    name="vpc-id",
    values=[vpc.id],
)])

# 2. Security Group
sg = aws.ec2.SecurityGroup("spilbloo-sg",
    vpc_id=vpc.id,
    description="Allow HTTP and SSH",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp", from_port=80, to_port=80, cidr_blocks=["0.0.0.0/0"]
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp", from_port=8000, to_port=8000, cidr_blocks=["0.0.0.0/0"]
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp", from_port=22, to_port=22, cidr_blocks=["0.0.0.0/0"]
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"]
        )
    ]
)

# 3. Persistent EBS Volume
# Pick the first subnet to get its AZ
if not subnets.ids:
    raise Exception("No subnets found in the default VPC")

first_subnet = aws.ec2.get_subnet(id=subnets.ids[0])

volume = aws.ebs.Volume("spilbloo-db-data",
    availability_zone=first_subnet.availability_zone,
    size=ebs_volume_size,
    type="gp3",
    tags={"Name": "spilbloo-db-data"}
)

# 4. IAM Role for EC2 to attach the volume
role = aws.iam.Role("spilbloo-ec2-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": { "Service": "ec2.amazonaws.com" },
                "Effect": "Allow",
                "Sid": ""
            }
        ]
    }"""
)

# Policy to allow volume attachment
policy = aws.iam.RolePolicy("spilbloo-ebs-policy",
    role=role.id,
    policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:AttachVolume",
                    "ec2:DescribeVolumes"
                ],
                "Resource": ["*"]
            }
        ]
    }"""
)

# Attach SSM Managed Instance Core policy to allow browser-based login (no .pem needed)
ssm_policy_attachment = aws.iam.RolePolicyAttachment("spilbloo-ssm-policy",
    role=role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
)

instance_profile = aws.iam.InstanceProfile("spilbloo-profile", role=role.name)

# 5. User Data Script for Auto-Recovery
user_data_script = volume.id.apply(lambda vol_id: f"""#!/bin/bash
yum update -y
yum install -y docker git
service docker start
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Wait for EBS volume and attach it
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
aws ec2 attach-volume --volume-id {vol_id} --instance-id $INSTANCE_ID --device /dev/xvdf --region $REGION

# Wait for device
while [ ! -b /dev/xvdf ]; do sleep 5; done

# Mount volume
mkdir -p /mnt/ebs_data
if ! blkid /dev/xvdf; then
    mkfs -t xfs /dev/xvdf
fi
mount /dev/xvdf /mnt/ebs_data
echo "/dev/xvdf /mnt/ebs_data xfs defaults,nofail 0 2" >> /etc/fstab

# Setup Application
cd /home/ec2-user
if [ ! -d "spilbloo-backend" ]; then
    git clone https://github.com/vikhil-byte/spilbloo_backend.git
fi
cd spilbloo-backend
git checkout develop
git pull origin develop

# Start Application
# docker-compose up -d

# Restart SSM Agent to ensure it picks up the IAM role credentials
systemctl restart amazon-ssm-agent
""")

# 6. Spot Instance
ami = aws.ec2.get_ami(most_recent=True, owners=["amazon"], filters=[
    aws.ec2.GetAmiFilterArgs(name="name", values=["al2023-ami-2023.*-arm64"]),
])

spot_instance = aws.ec2.SpotInstanceRequest("spilbloo-server",
    instance_type=instance_type,
    ami=ami.id,
    spot_price="0.01", # Max price for t4g.micro
    wait_for_fulfillment=True,
    key_name=key_name,
    vpc_security_group_ids=[sg.id],
    subnet_id=subnets.ids[0],
    iam_instance_profile=instance_profile.name,
    user_data=user_data_script,
    tags={"Name": "spilbloo-server"}
)

pulumi.export("public_ip", spot_instance.public_ip)
pulumi.export("volume_id", volume.id)

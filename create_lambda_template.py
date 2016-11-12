#!/usr/bin/env python3

#===============================================================================
#          FILE: create_lambda_template.py
#         USAGE: python create_lambda_template.py
#   DESCRIPTION: Create a Cloudformation template with an S3 bucket that involes a Lambda function.
#       OPTIONS: ---
#  REQUIREMENTS: ---
#          BUGS: ---
#         NOTES: ---
#        AUTHOR: Dan R. Mbanga
#  ORGANIZATION: Danulab
#       CREATED: 11/07/2016
#      REVISION: ---
#      Idver   : 1.1
#===============================================================================

from troposphere.constants import NUMBER
from troposphere import Template, Ref, Parameter, Join, GetAtt
from troposphere.s3 import Bucket, NotificationConfiguration, Filter, LambdaConfigurations, S3Key, Rules
from troposphere.awslambda import Function, Code, MEMORY_VALUES, Permission
from troposphere.iam import Role, Policy

#ref: http://docs.aws.amazon.com/AmazonS3/latest/API/RESTBucketPUTnotification.html

t = Template()

t.add_version("2010-09-09")

# Create the template

t.add_description(
    """
    AWS Cloudformation template for GzipToSnappy:
    This template creates a an S3 bucket and a Lambda function
    to trigger when gzip files are loaded on the S3 bucket.
     **WARNING**: You will be billed for AWS resources created.
    """
                  )

# Create parameters

inputBucketName = t.add_parameter(Parameter(
    "InputBucketName",
    Description="The name of the input bucket",
    Type="String"
))

inputKeyPrefix = t.add_parameter(Parameter(
    "InputKeyPrefix",
    Description="The S3 input folder for incoming files",
    Type="String",
    Default="stg/input-gz/"
))

outputBucketName = t.add_parameter(Parameter(
    "OutputBucketName",
    Description="The name of the output bucket. This is required",
    Type="String",
))

outputKeyPrefix = t.add_parameter(Parameter(
    "OutputKeyPrefix",
    Description="The S3 input folder for incoming files",
    Type="String",
    Default="stg/processed-snappy/"
))

codeBucketName = t.add_parameter(Parameter(
    "CodeBucketName",
    Description="Amazon S3 bucket name where the .zip file \
    containing your deployment package is stored.",
    Type="String",

))

codeS3Key = t.add_parameter(Parameter(
    "CodeS3Key",
    Description="The Amazon S3 object (the deployment package)\
     key name you want to upload",
    Type="String",
    Default="pub/gziptosnappy.zip"
))

functionName=t.add_parameter(Parameter(
    "FunctionName",
    Description="The name of the lambda function",
    Type="String",
    Default="gziptosnappy"
))


"""
Create S3 Bucket With a Notifications Configuration.
The bucket notifies the lambda function in case there is a PUT event.
"""

S3Bucket = t.add_resource(
    Bucket(
        "S3Bucket",
        BucketName=Ref(inputBucketName),
        NotificationConfiguration=NotificationConfiguration(
            LambdaConfigurations=[
                LambdaConfigurations(
                    Event="s3:ObjectCreated:*",
                    Filter=Filter(
                        S3Key=S3Key(
                            Rules=[Rules(Name="prefix", Value=Ref(inputKeyPrefix)),
                               Rules(Name="suffix", Value=".gz")]
                        )
                    ),
                    Function=Ref(functionName)
                )
            ]
        )

    )
)

BucketPermission = t.add_resource(
    Permission(
        "BucketPermission",
        Action="lambda:InvokeFunction",
        FunctionName= Ref(functionName),
        Principal= "s3.amazonaws.com",
        SourceAccount= Ref("AWS::AccountId"),
        SourceArn= Join("",["aws:arn:s3:::",Ref(S3Bucket)])
    )
)

"""
Create Lambda Function
"""

memorySize = t.add_parameter(Parameter(
    "LambdaMemorySize",
    Type=NUMBER,
    Default="512",
    Description="Amount of memory to allocate to the lambda function",
    AllowedValues=MEMORY_VALUES
))

timeout = t.add_parameter(Parameter(
    'LambdaTimeout',
    Type=NUMBER,
    Description='Timeout in seconds for the Lambda function',
    Default='180'
))


GzipToSnappyFunction = t.add_resource(
    Function(
        "GzipToSnappyFunction",
        FunctionName=Ref(functionName),
        Code=Code(
            S3Bucket=Ref(codeBucketName),
            S3Key=Ref(codeS3Key)
        ),
        Handler="gztosnappy.lambda_handler",
        Role=GetAtt("LambdaExecutionRole","Arn"),
        Runtime="python2.7",
        Timeout=Ref(timeout),
        MemorySize=Ref(memorySize)
    )
)

LambdaExecutionRole = t.add_resource(
    Role(
        "LambdaExecutionRole",
        Path="/",
        Policies=[
            Policy(
                PolicyName="LambdaGzToSnappy",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject"
                        ],
                        "Resource": [
                            Join(":",["arn", "aws", "s3", "", "",
                                      Join(
                                          "",[
                                              Join("/",[Ref(inputBucketName), Ref(inputKeyPrefix)]),"*"
                                            ]
                                      )
                                ]
                                 ),
                            Join(":", ["arn", "aws", "s3", "", "",
                                       Join(
                                           "", [
                                               Join("/", [Ref(outputBucketName), Ref(outputKeyPrefix)]), "*"
                                           ]
                                       )
                                       ]
                                 )

                        ]
                        },

                        {
                            "Action": ["logs:*"],
                            "Resource": "arn:aws:logs:*:*:*",
                            "Effect": "Allow"
                        }
                    ]
                }
            )
        ],
        AssumeRolePolicyDocument= {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["sts:AssumeRole"],
                    "Effect": "Allow",
                    "Principal": {
                        "Service": ["lambda.amazonaws.com"]
                    }
                }
            ]
        }
    )
)

print(t.to_json())
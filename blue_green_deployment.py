import boto3
import time

# AWS region and Lambda function name.
region = "<region>"
lambda_function_name = "BlueGreenLambda"

# Role ARN for Lambda.
role_arn = "arn:aws:iam::<acct#>:role/devops-lambda-execution-role"

# Initialize AWS Lambda client.
lambda_client = boto3.client("lambda", region_name=region)

# Function to wait until the Lambda function is active.
def wait_for_function_active(function_name):
    print(f"Waiting for function '{function_name}' to become active...")
    while True:
        response = lambda_client.get_function(FunctionName=function_name)
        state = response['Configuration']['State']
        if state == 'Active':
            print(f"Function '{function_name}' is now active.")
            break
        elif state == 'Failed':
            raise Exception(f"Function '{function_name}' failed to activate: {response['Configuration']['StateReason']}")
        else:
            print(f"Current state: {state}. Retrying in 5 seconds...")
            time.sleep(5)

# Deploy Blue version.
def deploy_blue():
    print(f"Deploying Blue version...")
    try:
        response = lambda_client.create_function(
            FunctionName=lambda_function_name,
            Runtime="python3.8",
            Role=role_arn,
            Handler="lambda_blue.lambda_handler",
            Code={"ZipFile": open("lambda_blue.zip", "rb").read()},
            Description="Blue version of the Lambda function",
            Publish=True,
        )
    except lambda_client.exceptions.ResourceConflictException:
        print(f"Function '{lambda_function_name}' already exists. Skipping creation.")
        response = lambda_client.get_function(FunctionName=lambda_function_name)
    wait_for_function_active(lambda_function_name)
    return response['Configuration']['Version']

# Deploy Green version.
def deploy_green():
    print("Deploying Green version...")
    response = lambda_client.update_function_code(
        FunctionName=lambda_function_name,
        ZipFile=open("lambda_green.zip", "rb").read(),
        Publish=True,
    )
    wait_for_function_active(lambda_function_name)
    return response['Version']

# Create or update an alias to switch traffic.
def create_or_update_alias(version, alias_name="live"):
    print(f"Updating alias '{alias_name}' to point to version {version}...")
    try:
        lambda_client.create_alias(
            FunctionName=lambda_function_name,
            Name=alias_name,
            FunctionVersion=version,
            Description=f"Alias pointing to version {version}",
        )
    except lambda_client.exceptions.ResourceConflictException:
        lambda_client.update_alias(
            FunctionName=lambda_function_name,
            Name=alias_name,
            FunctionVersion=version,
            Description=f"Alias updated to version {version}",
        )

def main():
    print("Starting Blue/Green Deployment...")

    # Deploy the Blue version and create the alias.
    blue_version = deploy_blue()
    create_or_update_alias(blue_version, "live")
    print(f"Blue version deployed and alias 'live' updated to version {blue_version}")

    # Wait for user confirmation to deploy the Green version.
    input("Press <Enter> to deploy the Green version...")

    # Deploy the Green version and update the alias.
    green_version = deploy_green()
    create_or_update_alias(green_version, "live")
    print(f"Green version deployed and alias 'live' updated to version {green_version}")

if __name__ == "__main__":
    main()

        

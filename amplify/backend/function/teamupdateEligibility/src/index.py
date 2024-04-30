import os
import boto3
import requests 
from requests_aws_sign import AWSV4Sign

def get_entitlements(id):
    dynamodb = boto3.resource("dynamodb")
    policy_table_name = os.getenv("POLICY_TABLE_NAME")
    policy_table = dynamodb.Table(policy_table_name)
    
    response = policy_table.get_item(Key={"id": id})
    return response


def fetch_sso_permissions(client):
    instance_arn = "arn:aws:sso:::instance/ssoins-82593d0974641adf"
    permission_sets = []

    # Initialize paginator for listing all permission sets
    paginator = client.get_paginator('list_permission_sets')
    page_iterator = paginator.paginate(InstanceArn=instance_arn)

    for page in page_iterator:
        for permission_set_arn in page['PermissionSets']:
            # For each permission set ARN, get detailed information
            response = client.describe_permission_set(
                InstanceArn=instance_arn,
                PermissionSetArn=permission_set_arn
            )
            permission_details = {
                "name": response['PermissionSet']['Name'],
                "id": permission_set_arn,
                "__typename": "data"
            }
            permission_sets.append(permission_details)

    return permission_sets


def update_entitlement_in_dynamodb(id, update_data):
    dynamodb = boto3.resource("dynamodb")
    policy_table_name = os.getenv("POLICY_TABLE_NAME")
    table = dynamodb.Table(policy_table_name)

    # Construct the update expression and attribute values
    update_expression = "SET "
    expression_attribute_values = {}
    expression_attribute_names = {}

    # Dynamically build the update expression based on data provided
    for key, value in update_data.items():
        update_expression += f"#{key} = :{key}, "
        expression_attribute_values[f":{key}"] = value
        expression_attribute_names[f"#{key}"] = key

    # Remove the trailing comma and space from the update expression
    update_expression = update_expression.rstrip(", ")

    try:
        response = table.update_item(
            Key={"id": id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames=expression_attribute_names,
            ReturnValues="UPDATED_NEW"
        )
        print("Update successful:", response)
    except Exception as e:
        print("Error updating DynamoDB:", e)
        return None

    return response


def handler(event, context):
    client = boto3.client('sso-admin')
    permissions = fetch_sso_permissions(client)
    
    # Suppose you get entitlement ID from the event object
    entitlement_id = "976718bcc5-02fb4dc8-ef82-4cd7-9531-cf06a3e3c87d"
    update_data = {
        "permissions": permissions
        # Add other fields you want to update
    }
    
    # Update entitlement data directly in DynamoDB
    update_response = update_entitlement_in_dynamodb(entitlement_id, update_data)
    print(update_response)

    # Return something useful or the response of the update
    return {
        "status": "success",
        "data": update_response
    }



# def send_graphql_mutation(query, variables):
#     print("UPDATE OBJECT: ", variables)

#     session = boto3.session.Session()
#     credentials = session.get_credentials().get_frozen_credentials()
#     region = session.region_name

#     auth = AWSV4Sign(credentials, region, "appsync")
#     print("AUTH: ", auth)

#     url = os.environ.get("API_TEAM_GRAPHQLAPIENDPOINTOUTPUT", None)

#     headers = {'Content-Type': 'application/json'}
#     payload = {'query': query, 'variables': variables}

#     try:
#         response = requests.post(url, auth=auth, json=payload, headers=headers).json()
#         print("Full response:", response)
#         if "errors" in response:
#             print("Error attempting to query AppSync")
#             print(response["errors"])
#         else:
#             print("Mutation successful.")
#             print(response)
#     except Exception as exception:
#         print("Error with Query")
#         print(exception)
#         return {'error': 'Failed to update eligibility', 'details': str(exception)}
    
#     return response


# def handler(event, context):
#     client = boto3.client('sso-admin')
#     permissions = fetch_sso_permissions(client)
    
#     entitlement = get_entitlements("976718bcc5-02fb4dc8-ef82-4cd7-9531-cf06a3e3c87d")
#     entitlement_data = entitlement.get('Item', {})
#     entitlement_data['permissions'] = permissions

#     graphql_query = """
#     mutation UpdateEligibility($input: UpdateEligibilityInput!, $condition: ModelEligibilityConditionInput) {
#         updateEligibility(input: $input, condition: $condition) {
#             id
#             name
#             type
#             accounts {
#                 name
#                 id
#                 __typename
#             }
#             ous {
#                 name
#                 id
#                 __typename
#             }
#             permissions {
#                 name
#                 id
#                 __typename
#             }
#             ticketNo
#             approvalRequired
#             duration
#             modifiedBy
#             createdAt
#             updatedAt
#             __typename
#         }
#     }
#     """
#     result = {'input': entitlement_data, 'condition': {}}
#     return send_graphql_mutation(graphql_query, result)
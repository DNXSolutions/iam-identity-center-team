import os
import json
import boto3
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

    paginator = client.get_paginator('list_permission_sets')
    page_iterator = paginator.paginate(InstanceArn=instance_arn)

    for page in page_iterator:
        for permission_set_arn in page['PermissionSets']:
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

    update_expression = "SET "
    expression_attribute_values = {}
    expression_attribute_names = {}

    for key, value in update_data.items():
        update_expression += f"#{key} = :{key}, "
        expression_attribute_values[f":{key}"] = value
        expression_attribute_names[f"#{key}"] = key

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


def is_data_same(current_data, new_data):
    return json.dumps(current_data, sort_keys=True) == json.dumps(new_data, sort_keys=True)


def handler(event, context):
    client = boto3.client('sso-admin')
    permissions = fetch_sso_permissions(client)
    
    entitlement_id = "976718bcc5-02fb4dc8-ef82-4cd7-9531-cf06a3e3c87d"
    current_data = get_entitlements(entitlement_id).get('Item', {})
    
    update_data = {
        "permissions": permissions
    }

    print("Current: ", json.dumps(current_data["permissions"], sort_keys=True))
    print("Updated: ", json.dumps(update_data, sort_keys=True))

    if is_data_same(current_data["permissions"], update_data):
        print("No changes detected, exiting...")
        return {"status": "no_change"}

    update_response = update_entitlement_in_dynamodb(entitlement_id, update_data)
    print(update_response)

    return {
        "status": "success",
        "data": update_response
    }
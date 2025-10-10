# api/services/cognito.py
import boto3
import hmac
import hashlib
import base64
from typing import Dict, Optional
from botocore.exceptions import ClientError
from api.config import settings

class CognitoService:
    def __init__(self):
        self.client = boto3.client('cognito-idp', region_name=settings.AWS_REGION)
        # Get User Pool details from CloudFormation outputs
        self.user_pool_id = self._get_user_pool_id()
        self.client_id = self._get_client_id()
        self.client_secret = None  # We created client WITHOUT secret
    
    def _get_user_pool_id(self) -> str:
        """Get User Pool ID from CloudFormation"""
        cfn = boto3.client('cloudformation', region_name=settings.AWS_REGION)
        try:
            response = cfn.describe_stacks(StackName='spinscribe-production')
            for output in response['Stacks'][0]['Outputs']:
                if output['OutputKey'] == 'UserPoolId':
                    return output['OutputValue']
        except:
            pass
        # Fallback - retrieve from Cognito directly
        pools = self.client.list_user_pools(MaxResults=50)
        for pool in pools['UserPools']:
            if 'spinscribe-production' in pool['Name']:
                return pool['Id']
        raise Exception("User Pool not found")
    
    def _get_client_id(self) -> str:
        """Get User Pool Client ID from CloudFormation"""
        cfn = boto3.client('cloudformation', region_name=settings.AWS_REGION)
        try:
            response = cfn.describe_stacks(StackName='spinscribe-production')
            for output in response['Stacks'][0]['Outputs']:
                if output['OutputKey'] == 'UserPoolClientId':
                    return output['OutputValue']
        except:
            pass
        raise Exception("User Pool Client ID not found")
    
    def signup(self, email: str, password: str, name: str) -> Dict:
        """Register a new user"""
        try:
            response = self.client.sign_up(
                ClientId=self.client_id,
                Username=email,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'name', 'Value': name}
                ]
            )
            return {
                'user_sub': response['UserSub'],
                'confirmed': response.get('UserConfirmed', False)
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                raise ValueError("User with this email already exists")
            elif error_code == 'InvalidPasswordException':
                raise ValueError("Password does not meet requirements")
            else:
                raise ValueError(f"Signup failed: {e.response['Error']['Message']}")
    
    def confirm_signup(self, email: str, code: str) -> bool:
        """Confirm user signup with verification code"""
        try:
            self.client.confirm_sign_up(
                ClientId=self.client_id,
                Username=email,
                ConfirmationCode=code
            )
            return True
        except ClientError as e:
            raise ValueError(f"Confirmation failed: {e.response['Error']['Message']}")
    
    def login(self, email: str, password: str) -> Dict:
        """Authenticate user and get tokens"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            
            auth_result = response['AuthenticationResult']
            return {
                'access_token': auth_result['AccessToken'],
                'refresh_token': auth_result['RefreshToken'],
                'id_token': auth_result['IdToken'],
                'expires_in': auth_result['ExpiresIn'],
                'token_type': auth_result['TokenType']
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UserNotConfirmedException':
                raise ValueError("Please verify your email first")
            elif error_code == 'NotAuthorizedException':
                raise ValueError("Invalid email or password")
            else:
                raise ValueError(f"Login failed: {e.response['Error']['Message']}")
    
    def refresh_token(self, refresh_token: str) -> Dict:
        """Refresh access token"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            auth_result = response['AuthenticationResult']
            return {
                'access_token': auth_result['AccessToken'],
                'id_token': auth_result['IdToken'],
                'expires_in': auth_result['ExpiresIn'],
                'token_type': auth_result['TokenType']
            }
        except ClientError as e:
            raise ValueError(f"Token refresh failed: {e.response['Error']['Message']}")
    
    def get_user_from_token(self, access_token: str) -> Dict:
        """Get user details from access token"""
        try:
            response = self.client.get_user(AccessToken=access_token)
            
            user_data = {
                'username': response['Username'],
                'user_sub': None,
                'email': None,
                'name': None
            }
            
            for attr in response['UserAttributes']:
                if attr['Name'] == 'sub':
                    user_data['user_sub'] = attr['Value']
                elif attr['Name'] == 'email':
                    user_data['email'] = attr['Value']
                elif attr['Name'] == 'name':
                    user_data['name'] = attr['Value']
            
            return user_data
        except ClientError as e:
            raise ValueError(f"Invalid token: {e.response['Error']['Message']}")
    
    def admin_delete_user(self, email: str):
        """Admin: Delete a user (for cleanup)"""
        try:
            self.client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=email
            )
        except ClientError as e:
            raise ValueError(f"User deletion failed: {e.response['Error']['Message']}")

# Singleton instance
cognito_service = CognitoService()
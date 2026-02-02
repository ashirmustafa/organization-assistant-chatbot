import json
import os
import msal
import requests
from datetime import datetime, timedelta

def get_graph_token():
    """
    Acquires an access token for Microsoft Graph API using Client Credentials Flow.
    Returns the token string or None if failed.
    """
    tenant_id = os.environ.get('TENANT_ID')
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scope = ["https://graph.microsoft.com/.default"]
    
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret
    )
    
    result = app.acquire_token_for_client(scopes=scope)
    
    if "access_token" in result:
        return result["access_token"]
    else:
        error = result.get("error_description", result.get("error", "Unknown error"))
        print(f"❌ Token acquisition failed: {error}")
        return None


# def search_user_by_name(token, search_name):
#     """
#     Searches for users by display name.
#     Returns list of matching users or None if failed.
#     """
#     headers = {
#         'Authorization': f'Bearer {token}',
#         'Content-Type': 'application/json'
#     }
    
#     url = f"https://graph.microsoft.com/v1.0/users?$filter=startswith(displayName,'{search_name}')&$select=id,displayName,userPrincipalName"
    
#     try:
#         response = requests.get(url, headers=headers, timeout=10)
#         response.raise_for_status()
        
#         users = response.json().get('value', [])
#         return [{'id': u['id'], 'name': u['displayName'], 'email': u['userPrincipalName']} for u in users]
        
#     except Exception as e:
#         print(f"❌ User search failed: {str(e)}")
#         return None


# def check_user_mailbox(token, user_id):
#     """
#     Checks if a user has a mailbox configured
#     """
#     headers = {
#         'Authorization': f'Bearer {token}',
#         'Content-Type': 'application/json'
#     }
    
#     # Try to get the user's mailbox settings
#     url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailboxSettings"
    
#     try:
#         response = requests.get(url, headers=headers, timeout=10)
#         print(f"📬 Mailbox check status: {response.status_code}")
#         print(f"📬 Mailbox response: {response.text[:500]}")  # First 500 chars
        
#         if response.status_code == 200:
#             return True
#         return False
        
#     except Exception as e:
#         print(f"❌ Mailbox check error: {str(e)}")
#         return False

def search_user_by_name(token, search_name):
    """
    Searches for users with prioritized matching:
    1. Exact match
    2. Starts with
    3. Contains (only if nothing found in 1 & 2)
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    search_name_lower = search_name.lower().strip()
    
    # Tier 1: Exact match on displayName
    print(f"🔍 Tier 1: Exact match search for '{search_name}'")
    url_exact = f"https://graph.microsoft.com/v1.0/users?$filter=tolower(displayName) eq '{search_name_lower}'&$select=id,displayName,userPrincipalName"
    
    try:
        response = requests.get(url_exact, headers=headers, timeout=10)
        if response.status_code == 200:
            users = response.json().get('value', [])
            if users:
                print(f"✅ Found {len(users)} exact match(es)")
                return [{'id': u['id'], 'name': u['displayName'], 'email': u['userPrincipalName']} for u in users]
    except Exception as e:
        print(f"⚠️ Exact match search failed: {e}")
    
    # Tier 2: Starts with
    print(f"🔍 Tier 2: Starts-with search for '{search_name}'")
    url_startswith = f"https://graph.microsoft.com/v1.0/users?$filter=startswith(tolower(displayName),'{search_name_lower}')&$select=id,displayName,userPrincipalName"
    
    try:
        response = requests.get(url_startswith, headers=headers, timeout=10)
        if response.status_code == 200:
            users = response.json().get('value', [])
            if users:
                print(f"✅ Found {len(users)} starts-with match(es)")
                return [{'id': u['id'], 'name': u['displayName'], 'email': u['userPrincipalName']} for u in users]
    except Exception as e:
        print(f"⚠️ Starts-with search failed: {e}")
    
    # Tier 3: Contains (fetch all and filter locally - last resort)
    print(f"🔍 Tier 3: Contains search (local filter) for '{search_name}'")
    url_all = f"https://graph.microsoft.com/v1.0/users?$select=id,displayName,userPrincipalName&$top=999"
    
    try:
        response = requests.get(url_all, headers=headers, timeout=10)
        if response.status_code == 200:
            all_users = response.json().get('value', [])
            matched_users = []
            seen_ids = set()
            
            for user in all_users:
                display_name_lower = user.get('displayName', '').lower()
                if search_name_lower in display_name_lower and user['id'] not in seen_ids:
                    seen_ids.add(user['id'])
                    matched_users.append({
                        'id': user['id'],
                        'name': user['displayName'],
                        'email': user['userPrincipalName']
                    })
            
            if matched_users:
                print(f"✅ Found {len(matched_users)} contains match(es)")
                return matched_users
    except Exception as e:
        print(f"⚠️ Contains search failed: {e}")
    
    # Nothing found
    print(f"❌ No users found matching '{search_name}'")
    return []


def get_user_calendar(token, user_id, days_ahead=1):
    """
    Fetches calendar events for a user.
    days_ahead: how many days in the future to look (default 1 = tomorrow)
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Prefer': 'outlook.timezone="UTC"'
    }
    
    # Calculate time range
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(days=days_ahead)
    
    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/calendarView?startDateTime={start_str}&endDateTime={end_str}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # Better error logging
        if response.status_code == 404:
            print(f"❌ 404 Error: User {user_id} has no mailbox or calendar access denied")
            print(f"Response: {response.text}")
            return None
        
        response.raise_for_status()
        
        events = response.json().get('value', [])
        
        # Format events for readability
        formatted = []
        for event in events:
            formatted.append({
                'subject': event.get('subject', 'No Subject'),
                'start': event['start']['dateTime'],
                'end': event['end']['dateTime'],
                'location': event.get('location', {}).get('displayName', 'No Location'),
                'organizer': event.get('organizer', {}).get('emailAddress', {}).get('name', 'Unknown')
            })
        
        return formatted
        
    except Exception as e:
        print(f"❌ Calendar fetch failed: {str(e)}")
        return None


def lambda_handler(event, context):
    """
    Main handler - Searches for user and fetches their calendar
    """
    try:
        # Parse input
        body = json.loads(event.get('body', '{}'))
        search_name = body.get('name')
        days_ahead = body.get('days', 1)  # Default to tomorrow
        
        if not search_name:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing "name" parameter'})
            }
        
        # Step 1: Get token
        print(f"🔐 Acquiring token...")
        token = get_graph_token()
        if not token:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Failed to acquire token'})
            }
        
        # Step 2: Find user
        print(f"🔍 Searching for user: {search_name}")
        users = search_user_by_name(token, search_name)
        
        # DEBUG LINE - Check what's being returned
        print(f"🔎 DEBUG: Found {len(users) if users else 0} user(s)")
        if users:
            for idx, u in enumerate(users):
                print(f"   [{idx}] {u.get('name')} ({u.get('email')})")
        
        if users is None or len(users) == 0:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': f'No user found with name "{search_name}"'})
            }
        
        if len(users) > 1:
            # Multiple matches - return them for user to clarify
            print(f"⚠️ Multiple users found, asking user to clarify")
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'Multiple users found. Please be more specific.',
                    'count': len(users),
                    'users': users
                })
            }
        
        # Step 3: Get calendar for the single matched user
        user = users[0]
        print(f"👤 Found user: {user['name']} ({user['email']})")
        
        # Step 4: Fetch calendar directly (no mailbox check needed!)
        print(f"📅 Fetching calendar for next {days_ahead} day(s)...")
        events = get_user_calendar(token, user['id'], days_ahead)
        
        if events is None:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f'Could not fetch calendar for {user["name"]}',
                    'hint': 'User may not have calendar access or Exchange license',
                    'user': user
                })
            }
        
        if len(events) == 0:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': f'{user["name"]} has no events in the next {days_ahead} day(s)',
                    'user': user,
                    'events': []
                })
            }
        
        # Success!
        print(f"✅ Successfully retrieved {len(events)} event(s)")
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': f'Found {len(events)} event(s) for {user["name"]}',
                'user': user,
                'events': events
            })
        }
        
    except Exception as e:
        print(f"❌ Lambda Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
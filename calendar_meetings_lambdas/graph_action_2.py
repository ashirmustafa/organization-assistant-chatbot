import json
import os
import msal
import requests
from datetime import datetime, timedelta

def get_graph_token():
    """
    Acquires an access token for Microsoft Graph API using Client Credentials Flow.
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


def search_user_by_name(token, search_name):
    """
    Searches for users with prioritized matching
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    search_name_lower = search_name.lower().strip()
    
    # Tier 1: Exact match
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
    
    # Tier 3: Contains
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
    
    print(f"❌ No users found matching '{search_name}'")
    return []


def parse_date_input(date_str):
    """
    Parses date input and returns a datetime object
    """
    date_str_lower = date_str.lower().strip()
    
    if date_str_lower in ['today', 'now']:
        return datetime.utcnow()
    elif date_str_lower == 'tomorrow':
        return datetime.utcnow() + timedelta(days=1)
    else:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print(f"⚠️ Could not parse date '{date_str}', defaulting to today")
            return datetime.utcnow()


def get_user_calendar(token, user_id, start_date_str=None, end_date_str=None):
    """
    Fetches calendar events for a user and converts times to Pakistan Standard Time (UTC+5)
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Prefer': 'outlook.timezone="UTC"'
    }
    
    if start_date_str:
        start_time = parse_date_input(start_date_str)
    else:
        start_time = datetime.utcnow()
    
    if end_date_str:
        end_time = parse_date_input(end_date_str)
        end_time = end_time + timedelta(days=1)
    else:
        end_time = start_time + timedelta(days=1)
    
    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
    
    print(f"📅 Querying calendar from {start_str} to {end_str}")
    
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/calendarView?startDateTime={start_str}&endDateTime={end_str}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            print(f"❌ 404 Error: User {user_id} has no mailbox")
            return None, None, None
        
        response.raise_for_status()
        
        events = response.json().get('value', [])
        
        formatted = []
        for event in events:
            # Get UTC times from Graph API
            utc_start = event['start']['dateTime']
            utc_end = event['end']['dateTime']
            
            try:
                # Remove 'Z' suffix if present and handle Microsoft's 7-digit microseconds
                utc_start_clean = utc_start.rstrip('Z')
                utc_end_clean = utc_end.rstrip('Z')
                
                # Split into datetime and fractional seconds
                if '.' in utc_start_clean:
                    # Has fractional seconds - truncate to 6 digits max for Python
                    date_part, frac_part = utc_start_clean.split('.')
                    utc_start_clean = f"{date_part}.{frac_part[:6]}"  # Keep only 6 digits
                
                if '.' in utc_end_clean:
                    date_part, frac_part = utc_end_clean.split('.')
                    utc_end_clean = f"{date_part}.{frac_part[:6]}"  # Keep only 6 digits
                
                # Parse datetime
                try:
                    start_dt = datetime.strptime(utc_start_clean, '%Y-%m-%dT%H:%M:%S.%f')
                    end_dt = datetime.strptime(utc_end_clean, '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    # No fractional seconds
                    start_dt = datetime.strptime(utc_start_clean, '%Y-%m-%dT%H:%M:%S')
                    end_dt = datetime.strptime(utc_end_clean, '%Y-%m-%dT%H:%M:%S')
                
                # Convert UTC to Pakistan Standard Time (UTC+5)
                pkt_start = start_dt + timedelta(hours=5)
                pkt_end = end_dt + timedelta(hours=5)
                
                # Format back to string
                formatted.append({
                    'subject': event.get('subject', 'No Subject'),
                    'start': pkt_start.strftime('%Y-%m-%dT%H:%M:%S'),  # Now in PKT
                    'end': pkt_end.strftime('%Y-%m-%dT%H:%M:%S'),      # Now in PKT
                    'location': event.get('location', {}).get('displayName', 'No Location'),
                    'organizer': event.get('organizer', {}).get('emailAddress', {}).get('name', 'Unknown'),
                    'timezone': 'PKT'  # Indicator that times are in Pakistan time
                })
                
                print(f"✅ Converted '{event.get('subject')}': {utc_start} → {pkt_start.strftime('%H:%M')} PKT")
                
            except Exception as parse_error:
                # If parsing fails, fall back to original times with warning
                print(f"⚠️ Could not parse time for '{event.get('subject')}': {parse_error}")
                formatted.append({
                    'subject': event.get('subject', 'No Subject'),
                    'start': utc_start,
                    'end': utc_end,
                    'location': event.get('location', {}).get('displayName', 'No Location'),
                    'organizer': event.get('organizer', {}).get('emailAddress', {}).get('name', 'Unknown'),
                    'timezone': 'UTC'  # Warning: couldn't convert
                })
        
        return formatted, start_time.strftime('%Y-%m-%d'), end_time.strftime('%Y-%m-%d')
        
    except Exception as e:
        print(f"❌ Calendar fetch failed: {str(e)}")
        return None, None, None


def create_calendar_event(token, organizer_email, event_details):
    """
    Creates a calendar event via Microsoft Graph API
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Parse start and end datetime
    try:
        start_dt = datetime.strptime(event_details['start_datetime'], '%Y-%m-%d %H:%M')
        
        # If end_datetime not provided, default to 1 hour after start
        if event_details.get('end_datetime'):
            end_dt = datetime.strptime(event_details['end_datetime'], '%Y-%m-%d %H:%M')
        else:
            end_dt = start_dt + timedelta(hours=1)
            print(f"⏱️ No end time provided, defaulting to 1 hour: {end_dt.strftime('%Y-%m-%d %H:%M')}")
        
    except ValueError as e:
        print(f"❌ Invalid datetime format: {e}")
        return {"error": "Invalid datetime format. Use 'YYYY-MM-DD HH:MM'"}
    
    # Build attendees list
    attendees_list = []
    for attendee in event_details.get('attendees', []):
        attendees_list.append({
            "emailAddress": {
                "address": attendee['email'],
                "name": attendee['name']
            },
            "type": "required"
        })
    
    # Build event payload
    event_payload = {
        "subject": event_details['subject'],
        "start": {
            "dateTime": start_dt.strftime('%Y-%m-%dT%H:%M:%S'),
            "timeZone": "Pakistan Standard Time"
        },
        "end": {
            "dateTime": end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
            "timeZone": "Pakistan Standard Time"
        },
        "attendees": attendees_list,
        "location": {
            "displayName": event_details.get('location', 'Microsoft Teams Meeting')
        },
        "isOnlineMeeting": event_details.get('is_online', True),
        "onlineMeetingProvider": "teamsForBusiness" if event_details.get('is_online', True) else None
    }
    
    # Remove onlineMeetingProvider if not online meeting
    if not event_details.get('is_online', True):
        del event_payload['onlineMeetingProvider']
    
    print(f"📤 Creating event for organizer: {organizer_email}")
    print(f"📋 Event payload: {json.dumps(event_payload, indent=2)}")
    
    url = f"https://graph.microsoft.com/v1.0/users/{organizer_email}/events"
    
    try:
        response = requests.post(url, headers=headers, json=event_payload, timeout=15)
        
        if response.status_code == 201:
            created_event = response.json()
            print(f"✅ Event created successfully! ID: {created_event.get('id')}")
            
            return {
                "success": True,
                "message": "Event created successfully",
                "event": {
                    "id": created_event.get('id'),
                    "subject": created_event.get('subject'),
                    "start": created_event['start']['dateTime'],
                    "end": created_event['end']['dateTime'],
                    "attendees": [{"name": a['name'], "email": a['email']} for a in event_details.get('attendees', [])],
                    "location": created_event.get('location', {}).get('displayName'),
                    "online_meeting_url": created_event.get('onlineMeeting', {}).get('joinUrl') if event_details.get('is_online') else None,
                    "organizer": event_details.get('organizer_name')
                }
            }
        else:
            error_text = response.text
            print(f"❌ Event creation failed: {response.status_code} - {error_text}")
            return {
                "success": False,
                "error": f"Failed to create event: {response.status_code}",
                "details": error_text
            }
            
    except Exception as e:
        print(f"❌ Exception during event creation: {str(e)}")
        return {
            "success": False,
            "error": f"Exception during event creation: {str(e)}"
        }


def send_email(token, sender_email, email_details):
    """
    NEW: Sends an email via Microsoft Graph API
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Build recipients list
    to_recipients = []
    for recipient in email_details.get('recipients', []):
        to_recipients.append({
            "emailAddress": {
                "address": recipient['email'],
                "name": recipient.get('name', recipient['email'])
            }
        })
    
    # Build CC list
    cc_recipients = []
    for cc in email_details.get('cc', []):
        cc_recipients.append({
            "emailAddress": {
                "address": cc['email'],
                "name": cc.get('name', cc['email'])
            }
        })
    
    # Build email payload
    message = {
        "message": {
            "subject": email_details['subject'],
            "body": {
                "contentType": "HTML",
                "content": email_details['body']
            },
            "toRecipients": to_recipients
        },
        "saveToSentItems": "true"
    }
    
    # Add CC if provided
    if cc_recipients:
        message["message"]["ccRecipients"] = cc_recipients
    
    print(f"📤 Sending email from: {sender_email}")
    print(f"📋 Email payload: {json.dumps(message, indent=2)}")
    
    url = f"https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail"
    
    try:
        response = requests.post(url, headers=headers, json=message, timeout=15)
        
        if response.status_code == 202:
            print(f"✅ Email sent successfully!")
            return {
                "success": True,
                "message": "Email sent successfully",
                "details": {
                    "subject": email_details['subject'],
                    "recipients": [r['email'] for r in email_details['recipients']],
                    "cc": [c['email'] for c in email_details.get('cc', [])]
                }
            }
        else:
            error_text = response.text
            print(f"❌ Email failed: {response.status_code} - {error_text}")
            return {
                "success": False,
                "error": f"Failed to send email: {response.status_code}",
                "details": error_text
            }
    except Exception as e:
        print(f"❌ Exception sending email: {e}")
        return {
            "success": False,
            "error": f"Exception sending email: {str(e)}"
        }


def lambda_handler(event, context):
    """
    Main handler - Routes between GET, CREATE, and SEND EMAIL actions
    """
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', 'get')  # Default to 'get' for backward compatibility
        
        print(f"🎬 Action: {action}")
        print(f"📦 Body: {json.dumps(body, indent=2)}")
        
        # Get token (used by all actions)
        token = get_graph_token()
        if not token:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Failed to acquire token'})
            }
        
        # Route to appropriate handler
        if action == 'create':
            # CREATE EVENT
            print("📝 Handling CREATE event request")
            
            result = create_calendar_event(token, body.get('organizer_id'), body)
            
            return {
                'statusCode': 200 if result.get('success') else 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(result)
            }
        
        elif action == 'send_email':
            # SEND EMAIL (NEW)
            print("📧 Handling SEND EMAIL request")
            
            result = send_email(token, body.get('sender_email'), body)
            
            return {
                'statusCode': 200 if result.get('success') else 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(result)
            }
        
        else:
            # GET EVENTS (existing logic)
            print("📅 Handling GET events request")
            
            search_name = body.get('name')
            start_date = body.get('start_date', 'today')
            end_date = body.get('end_date')
            
            # Backward compatibility with 'days'
            if 'days' in body:
                days_ahead = body.get('days', 1)
                start_date = 'today'
                if days_ahead == 0:
                    end_date = 'today'
                elif days_ahead == 1:
                    end_date = 'tomorrow'
                else:
                    end_dt = datetime.utcnow() + timedelta(days=days_ahead)
                    end_date = end_dt.strftime('%Y-%m-%d')
            
            if not search_name:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Missing "name" parameter'})
                }
            
            # Search for user
            users = search_user_by_name(token, search_name)
            
            if not users:
                return {
                    'statusCode': 404,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': f'No user found with name "{search_name}"'})
                }
            
            if len(users) > 1:
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'message': 'Multiple users found',
                        'count': len(users),
                        'users': users
                    })
                }
            
            # Single user found - get calendar
            user = users[0]
            events, actual_start, actual_end = get_user_calendar(token, user['id'], start_date, end_date)
            
            if events is None:
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({
                        'error': f'Could not fetch calendar for {user["name"]}',
                        'user': user
                    })
                }
            
            response_data = {
                'user': user,
                'events': events,
                'query_info': {
                    'start_date': actual_start,
                    'end_date': actual_end,
                    'event_count': len(events)
                }
            }
            
            if len(events) == 0:
                response_data['message'] = f'{user["name"]} has no events from {actual_start} to {actual_end}'
            else:
                response_data['message'] = f'Found {len(events)} event(s) for {user["name"]}'
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(response_data)
            }
        
    except Exception as e:
        print(f"❌ Lambda Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
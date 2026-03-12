import json
import os
import boto3
import msal
import requests
from datetime import datetime
from decimal import Decimal

# Initialize clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
table = dynamodb.Table('knowledge-base-chunks')

def get_graph_token():
    """Get Microsoft Graph access token"""
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
        raise Exception(f"Token acquisition failed: {result.get('error_description')}")

def get_sharepoint_files(token):
    """Download all files from SharePoint Company Resources folder"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Find SharePoint site
    site_search_url = "https://graph.microsoft.com/v1.0/sites?search=Puffersoft Team"
    site_response = requests.get(site_search_url, headers=headers, timeout=10)
    
    if site_response.status_code != 200:
        raise Exception(f"Site not found: {site_response.status_code}")
    
    sites = site_response.json().get('value', [])
    if not sites:
        raise Exception("Puffersoft Team site not found")
    
    site_id = sites[0]['id']
    print(f"✅ Found site: {sites[0].get('displayName')}")
    
    # Get files from Company Resources folder
    folder_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/Company Resources:/children"
    folder_response = requests.get(folder_url, headers=headers, timeout=10)
    
    if folder_response.status_code != 200:
        raise Exception(f"Folder access failed: {folder_response.status_code}")
    
    files = folder_response.json().get('value', [])
    print(f"📁 Found {len(files)} item(s)")
    
    documents = []
    
    for file_item in files:
        if not file_item.get('file'):
            continue
        
        file_name = file_item.get('name', '')
        file_id = file_item.get('id', '')
        file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
        if file_ext not in ['txt', 'pdf']:
            print(f"⏭️ Skipping: {file_name}")
            continue
        
        print(f"📄 Downloading: {file_name}")
        
        # Download file content
        content_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{file_id}/content"
        content_response = requests.get(content_url, headers=headers, timeout=30)
        
        if content_response.status_code != 200:
            print(f"⚠️ Failed to download {file_name}")
            continue
        
        # Extract text based on file type
        text_content = ""
        
        if file_ext == 'txt':
            text_content = content_response.text
        
        elif file_ext == 'pdf':
            try:
                import fitz  # PyMuPDF
                pdf_bytes = content_response.content
                pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                
                for page_num in range(pdf_document.page_count):
                    page = pdf_document[page_num]
                    text_content += page.get_text()
                
                pdf_document.close()
                print(f"✅ Extracted {len(text_content)} chars from {file_name}")
            
            except Exception as pdf_error:
                print(f"⚠️ PDF extraction error for {file_name}: {pdf_error}")
                continue
        
        if text_content.strip():
            documents.append({
                'filename': file_name,
                'content': text_content
            })
    
    return documents

def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk_content = text[start:end]
        
        if chunk_content.strip():
            chunks.append(chunk_content)
        
        start += chunk_size - overlap
    
    return chunks

def generate_embedding(text):
    """Generate embedding using Bedrock Titan"""
    try:
        response = bedrock_runtime.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({"inputText": text})
        )
        
        response_body = json.loads(response['body'].read())
        embedding = response_body['embedding']
        
        return embedding
    
    except Exception as e:
        print(f"⚠️ Embedding generation failed: {e}")
        return None

def store_chunks_in_dynamodb(documents):
    """Process documents and store chunks in DynamoDB"""
    total_chunks = 0
    
    # First, delete all existing chunks
    print("🗑️ Deleting old chunks from DynamoDB...")
    scan_response = table.scan()
    
    with table.batch_writer() as batch:
        for item in scan_response.get('Items', []):
            batch.delete_item(Key={'chunk_id': item['chunk_id']})
    
    print("✅ Old chunks deleted")
    
    # Process each document
    for doc in documents:
        filename = doc['filename']
        content = doc['content']
        
        print(f"\n📝 Processing: {filename}")
        
        # Split into chunks
        chunks = chunk_text(content)
        print(f"   Split into {len(chunks)} chunks")
        
        # Process each chunk
        for idx, chunk_content in enumerate(chunks):
            chunk_id = f"{filename}_chunk_{idx:04d}"
            
            # Generate embedding
            embedding = generate_embedding(chunk_content)
            
            if embedding is None:
                print(f"   ⚠️ Skipping chunk {idx} - embedding failed")
                continue

            decimal_embedding = [Decimal(str(f)) for f in embedding]
            
            # Store in DynamoDB
            item = {
                'chunk_id': chunk_id,
                'text': chunk_content,
                'embedding': decimal_embedding,
                'source_file': filename,
                'created_at': datetime.utcnow().isoformat()
            }
            
            table.put_item(Item=item)
            total_chunks += 1
            
            if (idx + 1) % 10 == 0:
                print(f"   Processed {idx + 1}/{len(chunks)} chunks")
        
        print(f"   ✅ Completed {filename}")
    
    return total_chunks

def lambda_handler(event, context):
    """Main indexing function"""
    try:
        print("🚀 Starting knowledge base indexing...")
        
        # Get Microsoft Graph token
        print("\n1️⃣ Getting Microsoft Graph token...")
        token = get_graph_token()
        print("   ✅ Token acquired")
        
        # Download files from SharePoint
        print("\n2️⃣ Downloading files from SharePoint...")
        documents = get_sharepoint_files(token)
        print(f"   ✅ Downloaded {len(documents)} documents")
        
        # Process and store chunks
        print("\n3️⃣ Processing documents and generating embeddings...")
        total_chunks = store_chunks_in_dynamodb(documents)
        
        print(f"\n✅ INDEXING COMPLETE!")
        print(f"   Documents processed: {len(documents)}")
        print(f"   Total chunks created: {total_chunks}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'documents_processed': len(documents),
                'total_chunks': total_chunks
            })
        }
    
    except Exception as e:
        print(f"\n❌ Indexing failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }

from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client.snipx

print("\n" + "="*60)
print("SUPPORT TICKETS CHECK")
print("="*60)

total_tickets = db.support_tickets.count_documents({})
print(f"\nTotal support tickets in database: {total_tickets}")

if total_tickets > 0:
    tickets = list(db.support_tickets.find({}).limit(10))
    
    print("\n📋 SUPPORT TICKETS:")
    for idx, ticket in enumerate(tickets, 1):
        subject = ticket.get('subject', 'N/A')
        message = ticket.get('message', 'N/A')
        status = ticket.get('status', 'N/A')
        created = ticket.get('created_at', 'N/A')
        user_id = ticket.get('user_id', 'N/A')
        
        print(f"\n{idx}. Ticket ID: {ticket['_id']}")
        print(f"   User ID: {user_id}")
        print(f"   Subject: {subject}")
        print(f"   Message: {message[:50]}..." if len(message) > 50 else f"   Message: {message}")
        print(f"   Status: {status}")
        print(f"   Created: {created}")
else:
    print("\n❌ NO SUPPORT TICKETS YET")
    print("\n💡 This means:")
    print("   - No users have submitted support requests")
    print("   - Support ticket form not being used")
    print("   - This is normal for new system")

print("\n" + "="*60)
print("HOW SUPPORT SYSTEM WORKS")
print("="*60)
print("""
1. USER SUBMITS TICKET:
   - Goes to /support page
   - Fills form (subject + message)
   - Clicks Submit
   - Ticket saved to database

2. ADMIN VIEWS TICKETS:
   - Goes to /admin/support
   - Sees all tickets from all users
   - Can filter by status (open/pending/closed)

3. ADMIN RESPONDS:
   - Clicks on ticket
   - Reads user's problem
   - Types response
   - Updates status

4. USER SEES RESPONSE:
   - Goes back to their support page
   - Sees admin's reply
   - Can reply back

⚠️  IT'S NOT LIVE CHAT!
   - It's like email support
   - Not real-time messaging
   - Both sides refresh to see updates
""")
print("="*60 + "\n")

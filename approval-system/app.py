import streamlit as st
import pandas as pd
from src.approval_system import (
    init_db,
    create_user,
    send_letter,
    list_pending_for_role,
    list_all_letters,
    act_on_letter,
    get_letter,
    get_letter_history,
)
import sqlite3
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Approval System",
    page_icon="📨",
    layout="wide"
)

# Database path
DB_PATH = "approval.db"

# Initialize database if needed
init_db(DB_PATH)

# Helper function to get all users
def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, name, role FROM users ORDER BY role, name")
    users = [dict(row) for row in cur.fetchall()]
    conn.close()
    return users

# Helper function to get user by ID
def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, name, role FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return dict(user) if user else None

# Sidebar for navigation
st.sidebar.title("📋 Approval System")
st.sidebar.markdown("---")

# User selection (simulate login)
users = get_all_users()
if users:
    user_options = {f"{u['name']} ({u['role']})": u['id'] for u in users}
    selected_user = st.sidebar.selectbox(
        "👤 Select User",
        options=list(user_options.keys())
    )
    current_user_id = user_options[selected_user]
    current_user = get_user_by_id(current_user_id)
    
    st.sidebar.success(f"Logged in as: **{current_user['name']}**")
    st.sidebar.info(f"Role: **{current_user['role']}**")
else:
    st.sidebar.warning("No users found. Please create users first.")
    current_user_id = None
    current_user = None

st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Menu",
    ["🏠 Dashboard", "📨 Send Letter", "📥 Pending Approvals", "📋 All Letters", "👥 Manage Users", "📊 Reports"]
)

# Main content area
st.title("📨 Approval Letter System")

if page == "🏠 Dashboard":
    st.header("Dashboard")
    
    # Get statistics
    all_letters = list_all_letters(DB_PATH)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Letters", len(all_letters))
    
    with col2:
        pending = len([l for l in all_letters if l['status'] == 'pending'])
        st.metric("Pending", pending)
    
    with col3:
        approved = len([l for l in all_letters if l['status'] == 'approved'])
        st.metric("Approved", approved)
    
    with col4:
        rejected = len([l for l in all_letters if l['status'] == 'rejected'])
        st.metric("Rejected", rejected)
    
    st.markdown("---")
    
    # Recent letters
    st.subheader("📌 Recent Letters")
    if all_letters:
        df = pd.DataFrame(all_letters)
        df = df[['id', 'title', 'sender_name', 'status', 'created_at']]
        df.columns = ['ID', 'Title', 'Sender', 'Status', 'Sent']
        st.dataframe(df, width='stretch')
    else:
        st.info("No letters yet")

elif page == "📨 Send Letter":
    st.header("Send New Letter")
    
    if current_user:
        # Define which roles can send letters
        SENDER_ROLES = ["Faculty Association", "Student", "SRC", "Staff", "SRC Member"]
        
        if current_user['role'] in SENDER_ROLES:
            with st.form("send_letter_form"):
                st.info(f"Sending as: **{current_user['name']}** ({current_user['role']})")
                
                title = st.text_input("Title", placeholder="Enter letter title")
                body = st.text_area("Body", placeholder="Enter letter content", height=200)
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("📤 Send Letter", type="primary")
                with col2:
                    st.form_submit_button("🗑️ Clear")
                
                if submitted and title and body:
                    try:
                        letter_id = send_letter(DB_PATH, current_user_id, title, body)
                        st.success(f"✅ Letter sent successfully! ID: {letter_id}")
                        
                        # Show the approval route
                        st.info("**Approval Route:**")
                        route = ["SRC", "Faculty", "HOD", "Dean", "Students Affairs Officer", 
                                "Dean of Student Affairs", "Vice Chancellor"]
                        for i, role in enumerate(route, 1):
                            st.write(f"{i}. {role}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.warning(f"⚠️ Your role '{current_user['role']}' cannot send letters.")
            st.info("✅ Allowed sender roles: " + ", ".join(SENDER_ROLES))
    else:
        st.warning("Please select a user from the sidebar.")

elif page == "📥 Pending Approvals":
    st.header("Pending Approvals")
    
    if current_user:
        # Get pending letters for current user's role
        pending = list_pending_for_role(DB_PATH, current_user['role'])
        
        if pending:
            st.success(f"You have {len(pending)} pending letter(s) to review")
            
            for letter in pending:
                with st.expander(f"📄 Letter #{letter['letter_id']}: {letter['title']}"):
                    st.write(f"**From:** {letter['sender_name']}")
                    st.write(f"**Sent:** {letter['created_at']}")
                    st.write(f"**Content:** {letter['body']}")
                    
                    # Action form
                    with st.form(f"action_form_{letter['letter_id']}"):
                        action = st.radio(
                            "Action",
                            ["approve", "reject"],
                            horizontal=True,
                            key=f"action_{letter['letter_id']}"
                        )
                        
                        comments = st.text_area(
                            "Comments",
                            placeholder="Add your comments...",
                            key=f"comments_{letter['letter_id']}"
                        )
                        
                        recommendations = st.text_area(
                            "Recommendations (optional)",
                            placeholder="Any recommendations for improvement?",
                            key=f"recs_{letter['letter_id']}"
                        )
                        
                        submitted = st.form_submit_button("Submit Decision", type="primary")
                        
                        if submitted:
                            try:
                                result = act_on_letter(
                                    DB_PATH,
                                    letter['letter_id'],
                                    current_user_id,
                                    action,
                                    comments,
                                    recommendations
                                )
                                
                                if action == "approve":
                                    if result['letter']['status'] == 'approved':
                                        st.success("✅ Letter fully approved!")
                                    else:
                                        next_step = result['current_step']
                                        st.success(f"✅ Approved! Next: {next_step['role']}")
                                else:
                                    st.warning("❌ Letter rejected")
                                
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
        else:
            st.info(f"No pending letters for your role ({current_user['role']})")
    else:
        st.warning("Please select a user from the sidebar.")

elif page == "📋 All Letters":
    st.header("All Letters")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "pending", "approved", "rejected"]
        )
    with col2:
        search = st.text_input("🔍 Search", placeholder="Search by title or content...")
    
    # Get letters
    letters = list_all_letters(DB_PATH)
    
    if letters:
        # Apply filters
        if status_filter != "All":
            letters = [l for l in letters if l['status'] == status_filter]
        
        if search:
            letters = [l for l in letters if 
                      search.lower() in l['title'].lower() or 
                      search.lower() in l.get('body', '').lower()]
        
        # Display letters
        for letter in letters:
            with st.expander(f"📄 Letter #{letter['id']}: {letter['title']} ({letter['status']})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**From:** {letter['sender_name']}")
                    st.write(f"**Status:** {letter['status']}")
                
                with col2:
                    st.write(f"**Sent:** {letter['created_at']}")
                
                st.write("**Content:**")
                st.write(letter.get('body', 'No content'))
                
                # View details button
                if st.button(f"View Full Details", key=f"view_{letter['id']}"):
                    st.session_state['view_letter'] = letter['id']
        
        # Show selected letter details
        if 'view_letter' in st.session_state:
            letter_id = st.session_state['view_letter']
            try:
                details = get_letter(DB_PATH, letter_id)
                
                st.markdown("---")
                st.subheader(f"📝 Letter #{letter_id} Details")
                
                # Approval steps
                st.write("**Approval History:**")
                steps_df = pd.DataFrame(details['steps'])
                if not steps_df.empty:
                    steps_df = steps_df[['step_index', 'role', 'status', 'actor_name', 'comments', 'acted_at']]
                    steps_df.columns = ['Step', 'Role', 'Status', 'Actor', 'Comments', 'Date']
                    st.dataframe(steps_df, width='stretch')
                
                if st.button("Close Details"):
                    del st.session_state['view_letter']
                    st.rerun()
            except Exception as e:
                st.error(f"Error loading details: {e}")
    else:
        st.info("No letters found")

elif page == "👥 Manage Users":
    st.header("Manage Users")
    
    tab1, tab2 = st.tabs(["View Users", "Create User"])
    
    with tab1:
        st.subheader("Current Users")
        users = get_all_users()
        if users:
            df = pd.DataFrame(users)
            st.dataframe(df, width='stretch')
        else:
            st.info("No users yet")
    
    with tab2:
        st.subheader("Create New User")
        
        with st.form("create_user_form"):
            name = st.text_input("Full Name", placeholder="Enter user's full name")
            
            role = st.selectbox(
                "Role",
                ["Faculty Association", "SRC", "Faculty", "HOD", "Dean", 
                 "Students Affairs Officer", "Dean of Student Affairs", "Vice Chancellor"]
            )
            
            submitted = st.form_submit_button("Create User", type="primary")
            
            if submitted and name:
                try:
                    user_id = create_user(DB_PATH, name, role)
                    st.success(f"✅ User created successfully! ID: {user_id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

elif page == "📊 Reports":
    st.header("Reports & Analytics")
    
    letters = list_all_letters(DB_PATH)
    
    if letters:
        df = pd.DataFrame(letters)
        
        # Status distribution
        st.subheader("Letter Status Distribution")
        status_counts = df['status'].value_counts()
        st.bar_chart(status_counts)
        
        # Letters over time
        st.subheader("Letters Over Time")
        df['date'] = pd.to_datetime(df['created_at']).dt.date
        daily_counts = df.groupby('date').size()
        st.line_chart(daily_counts)
        
        # Export
        if st.button("📥 Export to CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                "letters_export.csv",
                "text/csv"
            )
    else:
        st.info("No data for reports yet")
        
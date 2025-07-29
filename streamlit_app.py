import streamlit as st
import re
import json
from datetime import datetime, date, time as dt_time
from typing import Dict, Any, Optional
import asyncio
import os

# Import your existing modules (you'll need to adapt these)
# from src.rag_chain import ask_question
# from src.calendar_utils import create_event
# from src.email_utils import send_confirmation
# from src.content_filter import GuardrailsManager

# Configure Streamlit page
st.set_page_config(
    page_title="PsychBot - Dr. Sarah Tan's Clinic",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    
    .bot-message {
        background-color: #f1f8e9;
        border-left: 4px solid #4caf50;
    }
    
    .error-message {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
    
    .success-message {
        background-color: #e8f5e8;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .clinic-info {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Hello! I'm PsychBot, your virtual receptionist for Dr. Sarah Tan's psychotherapy clinic. How can I help you today?"
    })

if "booking_data" not in st.session_state:
    st.session_state.booking_data = {}

if "booking_mode" not in st.session_state:
    st.session_state.booking_mode = False

# Simplified content filter for Streamlit
class SimpleContentFilter:
    def __init__(self):
        self.crisis_patterns = [
            r'\b(?:suicide|kill\s+myself|end\s+my\s+life)\b',
            r'\b(?:hurt\s+myself|self\s+harm)\b',
        ]
        
        self.off_topic_patterns = [
            r'\b(?:weather|food|restaurant|movie|sports|politics)\b',
        ]
    
    def check_content(self, message: str) -> tuple[bool, str]:
        message_lower = message.lower()
        
        # Check for crisis
        for pattern in self.crisis_patterns:
            if re.search(pattern, message_lower):
                return False, """🚨 I'm concerned about your safety. Please reach out for immediate help:
                
• **Singapore Suicide Prevention Hotline: 1800-221-4444**
• **Emergency Services: 995**
• **Samaritans of Singapore: 1767**"""
        
        # Check for off-topic
        for pattern in self.off_topic_patterns:
            if re.search(pattern, message_lower):
                return False, "I'm here to help with questions about Dr. Sarah Tan's psychotherapy clinic and appointment bookings."
        
        return True, ""

# Initialize content filter
content_filter = SimpleContentFilter()

# Simplified RAG system for Streamlit
def get_clinic_response(question: str) -> str:
    """Simplified response system based on keywords"""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ["service", "offer", "therapy", "treatment"]):
        return """Dr. Tan offers several therapy services:
• Individual Therapy: $120 (50 minutes)
• Couples Therapy: $180 (80 minutes)  
• Family Therapy: $200 (90 minutes)
• Group Therapy: $60 (90 minutes)
• Online Therapy: $100 (50 minutes)

She specializes in CBT, DBT, anxiety, depression, and trauma treatment. Would you like to book an appointment?"""
    
    elif any(word in question_lower for word in ["hour", "time", "open", "when"]):
        return """Our clinic hours are:
• Monday-Friday: 9:00 AM - 7:00 PM
• Saturday: 9:00 AM - 5:00 PM  
• Sunday: Closed

Would you like to book an appointment?"""
    
    elif any(word in question_lower for word in ["where", "location", "address"]):
        return """We're located at:
📍 123 Therapy Street, Singapore 123456
📞 +65 6123 4567
✉️ appointments@drtanpsych.com

Would you like to book an appointment?"""
    
    elif any(word in question_lower for word in ["cost", "price", "fee", "much"]):
        return """Our session fees are:
• Individual Therapy: $120 (50 minutes)
• Couples Therapy: $180 (80 minutes)  
• Family Therapy: $200 (90 minutes)
• Group Therapy: $60 (90 minutes)
• Online Therapy: $100 (50 minutes)

Would you like to book an appointment?"""
    
    elif any(word in question_lower for word in ["doctor", "dr", "tan", "therapist", "qualification"]):
        return """Dr. Sarah Tan is our lead therapist with:
• Ph.D. in Clinical Psychology from NUS
• 12 years of clinical experience
• Licensed Clinical Psychologist
• Certified in CBT and DBT
• Fluent in English, Mandarin, and Hokkien

She specializes in anxiety, depression, trauma, and relationship counseling. Would you like to book an appointment?"""
    
    else:
        return """I'm here to help with information about Dr. Sarah Tan's psychotherapy clinic. I can tell you about:
• Our therapy services and pricing
• Dr. Tan's credentials and experience  
• Clinic hours and location
• How to book an appointment

What would you like to know?"""

# Booking information extraction
def extract_booking_info(message: str) -> Dict[str, Any]:
    """Extract booking information from message"""
    booking_info = {}
    message_upper = message.upper()
    
    # Extract NRIC
    nric_patterns = [
        r'\b[STFG]\d{7}[A-Z]\b',
        r'(?:NRIC|IC)(?:\s+is)?\s+([STFG]\d{7}[A-Z])\b',
        r'my\s+(?:NRIC|IC)\s+is\s+([STFG]\d{7}[A-Z])\b',
    ]
    
    for pattern in nric_patterns:
        nric_match = re.search(pattern, message_upper, re.IGNORECASE)
        if nric_match:
            if len(nric_match.groups()) > 0:
                booking_info['nric'] = nric_match.group(1)
            else:
                booking_info['nric'] = nric_match.group()
            break
    
    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, message)
    if email_match:
        booking_info['email'] = email_match.group().lower()
    
    # Extract name
    name_patterns = [
        r"(?:I'm|I am|My name is|Name is|name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*,?\s*(?:NRIC|IC))",
    ]
    
    for pattern in name_patterns:
        name_match = re.search(pattern, message, re.IGNORECASE)
        if name_match:
            potential_name = name_match.group(1).strip()
            potential_name = ' '.join(word.capitalize() for word in potential_name.split())
            if 2 <= len(potential_name) <= 50 and re.match(r'^[A-Za-z\s]+$', potential_name):
                booking_info['name'] = potential_name
                break
    
    # Extract date - simplified
    current_year = datetime.now().year
    month_patterns = [
        (r'\b(July|Jul)\s+(\d{1,2})\b', 7),
        (r'\b(\d{1,2})\s+(July|Jul)\b', 7),
        (r'\bon\s+(\d{1,2})\s+(July|Jul)\b', 7),
        (r'\b(August|Aug)\s+(\d{1,2})\b', 8),
        (r'\b(\d{1,2})\s+(August|Aug)\b', 8),
        (r'\bon\s+(\d{1,2})\s+(August|Aug)\b', 8),
    ]
    
    for pattern, month_num in month_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                if match.group(1).isdigit():
                    day = int(match.group(1))
                else:
                    day = int(match.group(2))
                
                if 1 <= day <= 31:
                    booking_info['date'] = f"{current_year}-{month_num:02d}-{day:02d}"
                    break
            except:
                continue
    
    # Extract time
    time_patterns = [
        (r'\bat\s+(\d{1,2})\s*(am|pm|AM|PM)\b', 'at_ampm'),
        (r'\b(\d{1,2})\s*(am|pm|AM|PM)\b', 'ampm_hour_only'),
    ]
    
    for pattern, time_type in time_patterns:
        time_match = re.search(pattern, message)
        if time_match:
            try:
                hour = int(time_match.group(1))
                ampm = time_match.group(2).lower()
                
                if ampm == 'pm' and hour != 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                
                booking_info['time'] = f"{hour:02d}:00"
                break
            except:
                continue
    
    return booking_info

def is_booking_complete(booking_info: Dict[str, Any]) -> tuple[bool, list]:
    """Check if booking is complete"""
    required_fields = ['name', 'nric', 'email', 'date', 'time']
    missing_fields = []
    
    for field in required_fields:
        if field not in booking_info or not booking_info[field]:
            missing_fields.append(field)
    
    return len(missing_fields) == 0, missing_fields

def process_booking(booking_data: Dict[str, Any]) -> str:
    """Process the booking (simplified for demo)"""
    try:
        # In a real app, you'd integrate with calendar and email APIs
        appointment_date = datetime.strptime(booking_data['date'], '%Y-%m-%d').date()
        appointment_time = datetime.strptime(booking_data['time'], '%H:%M').time()
        appointment_datetime = datetime.combine(appointment_date, appointment_time)
        
        # For demo purposes, we'll just return a success message
        return f"""✅ **Appointment Successfully Booked!**

📅 **Appointment Details:**
• Patient: {booking_data['name']}
• Date & Time: {appointment_datetime.strftime('%A, %B %d, %Y at %I:%M %p')}
• Location: 123 Therapy Street, Singapore 123456

📧 A confirmation email would be sent to {booking_data['email']}

*Note: This is a demo. In the live version, calendar invites and emails would be sent automatically.*"""
        
    except Exception as e:
        return f"❌ Sorry, there was an error processing your booking: {str(e)}"

# Main app layout
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🧠 PsychBot</h1>
        <p>Your virtual receptionist for Dr. Sarah Tan's Psychotherapy Clinic</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create two columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("💬 Chat with PsychBot")
        
        # Display chat messages
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>You:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message bot-message">
                    <strong>PsychBot:</strong> {message["content"]}
                </div>
                """, unsafe_allow_html=True)
        
        # Chat input
        if prompt := st.chat_input("Ask about our services, Dr. Tan's credentials, or say 'book appointment'..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Check content filter
            is_allowed, filter_response = content_filter.check_content(prompt)
            
            if not is_allowed:
                response = filter_response
            else:
                # Check if this is a booking attempt
                booking_keywords = ["book", "appointment", "schedule", "reserve"]
                has_booking_info = any([
                    re.search(r'\b[STFG]\d{7}[A-Z]\b', prompt.upper()),
                    re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', prompt),
                    any(keyword in prompt.lower() for keyword in booking_keywords)
                ])
                
                if has_booking_info:
                    # Extract booking info
                    new_booking_info = extract_booking_info(prompt)
                    st.session_state.booking_data.update(new_booking_info)
                    
                    # Check if complete
                    is_complete, missing_fields = is_booking_complete(st.session_state.booking_data)
                    
                    if is_complete:
                        response = process_booking(st.session_state.booking_data)
                        # Clear booking data after successful booking
                        st.session_state.booking_data = {}
                    else:
                        # Ask for missing info
                        response_parts = ["Thank you! Let me check what else I need:\n"]
                        
                        if st.session_state.booking_data:
                            response_parts.append("✅ **Information I have:**")
                            for key, value in st.session_state.booking_data.items():
                                if key == 'date':
                                    formatted_date = datetime.strptime(value, '%Y-%m-%d').strftime('%B %d, %Y')
                                    response_parts.append(f"• Date: {formatted_date}")
                                elif key == 'time':
                                    time_obj = datetime.strptime(value, '%H:%M').time()
                                    formatted_time = time_obj.strftime('%I:%M %p')
                                    response_parts.append(f"• Time: {formatted_time}")
                                else:
                                    response_parts.append(f"• {key.title()}: {value}")
                            response_parts.append("")
                        
                        response_parts.append("❓ **Still need:**")
                        field_prompts = {
                            'name': "• Your full name",
                            'nric': "• Your NRIC/FIN number (e.g., S1234567A)",
                            'email': "• Your email address",
                            'date': "• Preferred appointment date (e.g., August 15)",
                            'time': "• Preferred appointment time (e.g., 3pm)"
                        }
                        
                        for field in missing_fields:
                            if field in field_prompts:
                                response_parts.append(field_prompts[field])
                        
                        response_parts.append("\nPlease provide the missing information!")
                        response = "\n".join(response_parts)
                else:
                    # Regular question
                    response = get_clinic_response(prompt)
            
            # Add bot response
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.experimental_rerun()
    
    with col2:
        st.header("📍 Clinic Information")
        
        st.markdown("""
        <div class="clinic-info">
            <h4>Dr. Sarah Tan's Psychotherapy Clinic</h4>
            <p>📍 123 Therapy Street, Singapore 123456</p>
            <p>📞 +65 6123 4567</p>
            <p>✉️ appointments@drtanpsych.com</p>
            
            <h5>Operating Hours:</h5>
            <p>Monday - Friday: 9:00 AM - 7:00 PM</p>
            <p>Saturday: 9:00 AM - 5:00 PM</p>
            <p>Sunday: Closed</p>
            
            <h5>Services & Pricing:</h5>
            <p>• Individual Therapy: $120 (50 min)</p>
            <p>• Couples Therapy: $180 (80 min)</p>
            <p>• Family Therapy: $200 (90 min)</p>
            <p>• Group Therapy: $60 (90 min)</p>
            <p>• Online Therapy: $100 (50 min)</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Booking form as alternative
        st.header("📅 Quick Booking Form")
        
        with st.form("booking_form"):
            name = st.text_input("Full Name", placeholder="e.g., John Tan")
            email = st.text_input("Email", placeholder="john@example.com")
            nric = st.text_input("NRIC/FIN", placeholder="S1234567A")
            appt_date = st.date_input("Appointment Date", min_value=datetime.now().date())
            appt_time = st.time_input("Appointment Time")
            
            submitted = st.form_submit_button("Book Appointment")
            
            if submitted:
                if all([name, email, nric, appt_date, appt_time]):
                    # Validate NRIC pattern
                    if re.match(r'^[STFG]\d{7}[A-Z]$', nric.upper()):
                        appointment_datetime = datetime.combine(appt_date, appt_time)
                        
                        success_msg = f"""✅ **Appointment Successfully Booked!**

📅 **Details:**
• Patient: {name}
• Date & Time: {appointment_datetime.strftime('%A, %B %d, %Y at %I:%M %p')}
• Email: {email}

*Note: This is a demo. In the live version, calendar invites and emails would be sent automatically.*"""
                        
                        st.success(success_msg)
                    else:
                        st.error("Please enter a valid NRIC format (e.g., S1234567A)")
                else:
                    st.error("Please fill in all required fields")

if __name__ == "__main__":
    main()

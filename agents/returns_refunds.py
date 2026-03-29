
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('returns_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from state import AgentState, Message
from agents.base_agent import BaseAgent
from langchain_core.prompts import ChatPromptTemplate
import json


class ReturnsRefundsAgent(BaseAgent):
    def __init__(self, llm_model: str = "gpt-4"):
        """Initialize Returns & Refunds Agent"""
        super().__init__(
            agent_name="Returns & Refunds Agent",
            llm_model=llm_model
        )
        self.return_window_days = 30
        self.refund_policies = {
            "unopened": 1.00,      
            "used": 0.80,         
            "damaged": 1.00,       
            "defective": 1.00      
        }
    
    def get_system_prompt(self) -> str:
        return """You are a Returns & Refunds Agent for an e-commerce platform.
Your primary responsibilities:
1. Help customers initiate returns
2. Process refunds based on product condition
3. Track return status
4. Handle complaints and escalations
5. Provide return policy information

Return Policy:
- Return Window: 30 days from purchase
- Refund Based on Condition:
  * Unopened/Original Packaging: 100% refund
  * Used but in Good Condition: 80% refund
  * Damaged by Customer: Subject to inspection
  * Defective/Manufacturer Defect: 100% refund
- Return Shipping: FREE (we arrange pickup)
- Refund Processing: 5-7 business days after inspection
- Inspection Period: 1-3 days after receiving item

Your Approach:
1. Always verify return eligibility FIRST
2. Ask about product condition
3. Calculate accurate refund
4. Offer free return pickup
5. Track return progress
6. Escalate to human if needed

Customer Service Guidelines:
- Be empathetic and professional
- Provide clear, detailed information
- Follow company policies strictly
- Escalate complaints appropriately
- Always offer solutions

Available Information to Check:
- Order eligibility
- Product condition assessment
- Refund calculation
- Return status tracking
- Complaint escalation"""
    
    def invoke(self, state: AgentState) -> AgentState:
        try:
            state["current_agent"] = self.agent_name

            logger.info(f"Processing query: {state['user_query']}")
            logger.info(f"User ID: {state['user_id']}, Session: {state['session_id']}")
          
            if not self._is_return_query(state["user_query"]):
                state["route_to_agent"] = "coordinator"
                state["response"] = "This query is not about returns or refunds. Let me route you to the appropriate agent."
                state["success"] = True
                return state
            
           
            intent = self._determine_intent(state["user_query"])
            state["query_intent"] = intent

         
            logger.info(f"Intent detected: {intent}")
          
            
           
            if intent == "check_eligibility":
                state = self._handle_eligibility_check(state)
            elif intent == "initiate_return":
                state = self._handle_return_initiation(state)
            elif intent == "track_return":
                state = self._handle_return_tracking(state)
            elif intent == "complaint":
                state = self._handle_complaint(state)
            elif intent == "refund_status":
                state = self._handle_refund_status(state)
            else:
                state = self._handle_general_return_question(state)
            
            state["success"] = True
            self._add_to_history(state, state["response"])

         
            logger.info(f"Successfully processed. Response: {state['response'][:100]}...")
            logger.info(f"Tools used: {state['tools_used']}")
       
            
        except Exception as e:
            state["success"] = False
            state["error_message"] = f"Returns Agent Error: {str(e)}"

         
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
       
    
            state["response"] = f"I encountered an error: {str(e)}. Please contact support."
        
        return state
    
    def _is_return_query(self, query: str) -> bool:
        return_keywords = [
            "return", "refund", "broken", "damaged", "defective",
            "not working", "complaint", "unhappy", "issue",
            "send back", "money back", "replace", "exchange",
            "wrong item", "not as described", "track return"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in return_keywords)
    
    def _determine_intent(self, query: str) -> str:
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["check", "eligible", "can i return", "can i", "am i"]):
            return "check_eligibility"
        
        if any(word in query_lower for word in ["want to return", "start return", "initiate return", "return my"]):
            return "initiate_return"
        
        if any(word in query_lower for word in ["track", "status", "where", "when", "progress"]):
            return "track_return"
        
        if any(word in query_lower for word in ["refund", "money", "payment", "when will"]):
            return "refund_status"
        
        if any(word in query_lower for word in ["complaint", "issue", "problem", "broken", "damaged", "defective"]):
            return "complaint"
        
        return "general_question"
    
    def _calculate_confidence(self, intent: str) -> float:

        confidence_scores = {
          "check_eligibility": 0.95, 
          "initiate_return": 0.90,       
          "track_return": 0.85,         
          "refund_status": 0.85,          
          "complaint": 0.70,              
          "general_question": 0.95,      
        }
    
        return confidence_scores.get(intent, 0.80)
    
    def _generate_explanation(self, intent: str) -> str:
       explanations = {
        "check_eligibility": "Response based on 30-day return window and eligibility criteria",
        "initiate_return": "Gathering customer information to process return request",
        "track_return": "Providing return journey information and timeline",
        "refund_status": "Explaining refund processing timeline and expected arrival",
        "complaint": "Complaint escalated to support specialist for investigation",
        "general_question": "Response based on company return and refund knowledge base",
       }
    
       return explanations.get(intent, "Response from knowledge base")
    
    def _handle_eligibility_check(self, state: AgentState) -> AgentState:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("human", """Customer is asking about return eligibility.

Query: {query}

Conversation Context:
{context}

Please:
1. Explain our 30-day return window
2. Ask for order details if needed
3. Be clear about what items are returnable
4. Ask about product condition
5. Provide next steps if eligible""")
        ])
        
        response = self._call_llm(state, prompt)
        state["response"] = response
        state["tools_used"].append("eligibility_check")
        
  
        confidence = self._calculate_confidence(state["query_intent"])
        state["confidence_score"] = confidence

        if confidence < 0.75:
           logger.warning(f"Low confidence ({confidence}) for intent: {state['query_intent']}")
       

        return state
    
    def _handle_return_initiation(self, state: AgentState) -> AgentState:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("human", """Customer wants to initiate a return.

Query: {query}

Conversation Context:
{context}

Please:
1. Confirm order details (ask if needed)
2. Ask why they want to return
3. Ask about item condition
4. Explain our return process
5. Offer free return shipping
6. Provide estimated timeline
7. Ask if they want to proceed""")
        ])
        
        response = self._call_llm(state, prompt)
        state["response"] = response
        state["tools_used"].append("return_initiation")

      
        confidence = self._calculate_confidence(state["query_intent"])
        state["confidence_score"] = confidence
        state["explanation"] = self._generate_explanation(state["query_intent"])
    
        if confidence < 0.75:
          logger.warning(f"Low confidence ({confidence}) for intent: {state['query_intent']}")
        
        return state
    
    def _handle_return_tracking(self, state: AgentState) -> AgentState:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("human", """Customer wants to track their return.

Query: {query}

Conversation Context:
{context}

Please:
1. Ask for Return ID or Order Number
2. Explain what information we need
3. Describe what the return journey looks like
4. Provide typical timelines
5. Offer to help with next steps""")
        ])
        
        response = self._call_llm(state, prompt)
        state["response"] = response
        state["tools_used"].append("return_tracking")

        confidence = self._calculate_confidence(state["query_intent"])
        state["confidence_score"] = confidence
        state["explanation"] = self._generate_explanation(state["query_intent"])
  
        return state
    
    def _handle_refund_status(self, state: AgentState) -> AgentState:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("human", """Customer is asking about their refund status.

Query: {query}

Conversation Context:
{context}

Please:
1. Ask for Return ID if not provided
2. Explain refund timeline (5-7 days typical)
3. Explain the stages:
   - Item inspection: 1-3 days
   - Refund processing: 1-2 days
   - Bank processing: 3-5 days
4. Answer any concerns about the timeline
5. Provide support options""")
        ])
        
        response = self._call_llm(state, prompt)
        state["response"] = response
        state["tools_used"].append("refund_status")

     
        confidence = self._calculate_confidence(state["query_intent"])
        state["confidence_score"] = confidence
        state["explanation"] = self._generate_explanation(state["query_intent"])

        return state
    
    def _handle_complaint(self, state: AgentState) -> AgentState:

        logger.warning(f"COMPLAINT DETECTED: {state['user_query']}")

        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("human", """Customer has a complaint about a product.

Query: {query}

Conversation Context:
{context}

Please:
1. Show empathy and apologize for the issue
2. Understand the specific problem
3. Ask relevant follow-up questions
4. For damaged items: Offer immediate replacement OR full refund
5. For defective items: Offer full refund + replacement
6. For wrong items: Offer return + correct item shipped
7. Offer escalation to specialist if needed
8. Be helpful and solution-focused""")
        ])
        
        response = self._call_llm(state, prompt)
        state["response"] = response
        state["tools_used"].append("complaint_handling")
        state["escalation_reason"] = "Customer complaint - investigation needed"

        confidence = self._calculate_confidence(state["query_intent"])
        state["confidence_score"] = confidence
        state["explanation"] = self._generate_explanation(state["query_intent"])
    
        logger.info(f"Complaint escalated with confidence: {confidence}")
        
        return state
    
    def _handle_general_return_question(self, state: AgentState) -> AgentState:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("human", """Customer has a general question about returns.

Query: {query}

Conversation Context:
{context}

Please:
1. Understand what they want to know
2. Provide clear, helpful information
3. Reference our return policy where relevant
4. Offer additional help if needed""")
        ])
        
        response = self._call_llm(state, prompt)
        state["response"] = response
        state["tools_used"].append("general_info")

        confidence = self._calculate_confidence(state["query_intent"])
        state["confidence_score"] = confidence
        state["explanation"] = self._generate_explanation(state["query_intent"])
        
        return state


# Tool Functions - Can be called by agents or coordinator

def check_return_eligibility(order_id: str, purchase_date: str = None) -> Dict[str, Any]:
    if not purchase_date:
        purchase_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
    
    purchase_datetime = datetime.strptime(purchase_date, "%Y-%m-%d")
    days_elapsed = (datetime.now() - purchase_datetime).days
    days_remaining = 30 - days_elapsed
    
    return {
        "order_id": order_id,
        "eligible": days_remaining > 0,
        "days_remaining": max(0, days_remaining),
        "days_elapsed": days_elapsed,
        "purchase_date": purchase_date,
        "message": f"Order is {days_elapsed} days old. {days_remaining} days remaining to return." if days_remaining > 0 else "Order is outside 30-day return window."
    }


def calculate_refund_amount(
    order_id: str,
    original_price: float,
    condition: str,
    shipping_cost: float = 0.0
) -> Dict[str, Any]:
    refund_percentages = {
        "unopened": 1.00,
        "used": 0.80,
        "damaged": 1.00,
        "defective": 1.00,
    }
    
    percentage = refund_percentages.get(condition.lower(), 0.80)
    refund_amount = original_price * percentage
    
    # Include shipping refund
    include_shipping = condition.lower() in ["unopened", "damaged", "defective"]
    if include_shipping:
        refund_amount += shipping_cost
    
    return {
        "order_id": order_id,
        "original_price": original_price,
        "condition": condition,
        "refund_percentage": percentage * 100,
        "refund_amount": refund_amount,
        "includes_shipping": include_shipping,
        "shipping_refund": shipping_cost if include_shipping else 0,
        "message": f"Refund of ${refund_amount:.2f} calculated for {condition} item."
    }


def initiate_return(order_id: str, reason: str) -> Dict[str, Any]:
    return_id = f"RET_{order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "return_id": return_id,
        "order_id": order_id,
        "reason": reason,
        "status": "initiated",
        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": f"Return {return_id} initiated for order {order_id}."
    }


def arrange_pickup(return_id: str, address: str) -> Dict[str, Any]:
    pickup_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    tracking_number = f"TRK_{return_id}"
    
    return {
        "pickup_id": f"PU_{return_id}",
        "return_id": return_id,
        "scheduled_date": pickup_date,
        "tracking_number": tracking_number,
        "carrier": "FedEx",
        "address": address,
        "label_url": f"https://example.com/return-labels/{return_id}.pdf",
        "message": f"Pickup scheduled for {pickup_date}. FedEx tracking: {tracking_number}"
    }


def track_return_status(return_id: str) -> Dict[str, Any]:
    return {
        "return_id": return_id,
        "current_status": "received_at_facility",
        "status_message": "Item received and being inspected",
        "timeline": [
            {"date": "2026-02-01", "event": "Return initiated", "status": "completed"},
            {"date": "2026-02-02", "event": "Pickup scheduled", "status": "completed"},
            {"date": "2026-02-05", "event": "Item picked up", "status": "completed"},
            {"date": "2026-02-08", "event": "Item received at facility", "status": "completed"},
            {"date": "2026-02-10", "event": "Inspection completed", "status": "in_progress"},
            {"date": "2026-02-11", "event": "Refund processed", "status": "pending"},
        ],
        "estimated_refund_date": "2026-02-11"
    }


def process_refund(return_id: str, refund_amount: float) -> Dict[str, Any]:
    transaction_id = f"TXN_{return_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    expected_arrival = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    return {
        "transaction_id": transaction_id,
        "return_id": return_id,
        "refund_amount": refund_amount,
        "status": "processing",
        "expected_arrival": expected_arrival,
        "refund_method": "Original Payment Method",
        "message": f"Refund of ${refund_amount:.2f} processing. Expected in 5-7 business days."
    }


def escalate_complaint(return_id: str, reason: str) -> Dict[str, Any]:
    return {
        "escalation_id": f"ESC_{return_id}",
        "return_id": return_id,
        "reason": reason,
        "priority": "HIGH",
        "assigned_to": "Support Specialist",
        "expected_response_time": "Within 2 hours",
        "message": "Your complaint has been escalated. A specialist will contact you shortly."
    }

import os
from dotenv import load_dotenv

from typing import Literal, Optional
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
# from tools import tools


# Load environment variables from .env file
load_dotenv(override=True)


# -- Pydantic Schemas ---------------------
class IntentOutput(BaseModel):
    intent: Literal["sales", "recommend", "none"]


class ProductSearch(BaseModel):
    product_category: Optional[Literal['Electronics', 'Footwear', 'Clothing', 'Home Appliances']] = Field(description="The broad category of the product")
    product_subcategory: Optional[Literal['Mouse', 'Keyboard', 'Monitor', 'Headphones', 'Camera', 'Drone', 'Wearable', 'Sports Shoes', 'Boots', 'Jeans', 'Pants', 'T‑Shirts', 'Hoodies', 'Jackets', 'Sweaters', 'Vacuum Cleaner', 'Blender', 'Mixer', 'Pressure Cooker', 'Refrigerator', 'Washer', 'Television', 'Floor Cleaner', 'Gaming Console']] = Field(description="The specific category of the product")
    brand_name: Optional[Literal['Logitech', 'Razer', 'Apple', 'Corsair', 'Samsung', 'LG', 'Sony', 'Bose', 'Beats', 'Google', 'Canon', 'Nikon', 'DJI', 'Fitbit', 'Nike', 'Adidas', 'New Balance', 'Saucony', 'Timberland', 'Dr. Martens', 'Columbia', 'UGG', "Levi's", 'Wrangler', 'Gap', 'Uniqlo', 'Hanes', 'Champion', 'The North Face', 'Patagonia', 'Dyson', 'iRobot', 'Ninja', 'KitchenAid', 'Instant Pot', 'Bissell', 'Miele', 'Microsoft', 'Nintendo']] = Field(description="The brand of the product")
    min_price: Optional[float] = Field(description="The minimum price of the product")
    max_price: Optional[float] = Field(description="The maximum price of the product")
    min_rating: Optional[float] = Field(description="The minimum rating that the product has")
    max_rating: Optional[float] = Field(description="The maximum rating that the product has")


# -- LLM instance -------------------------
intent_llm = ChatOpenAI(model="gpt-5-nano",
                         temperature=0,
                         api_key=os.environ.get("OPENAI_API_KEY"),
                         use_responses_api=False,
                         max_completion_tokens=8192,
                         max_retries=2,
                         stream_usage=False
                         ).with_structured_output(IntentOutput)


# Tools must be bound to the LLM in order for it to work
# search_llm = ChatOpenAI(model="gpt-5-nano",
#                          temperature=0,
#                          api_key=os.environ.get("OPENAI_API_KEY"),
#                          use_responses_api=False,
#                          max_completion_tokens=8192,
#                          max_retries=2,
#                          stream_usage=False
#                          ).bind_tools(tools)

search_llm = ChatOpenAI(model="gpt-5-nano",
                         temperature=0,
                         api_key=os.environ.get("OPENAI_API_KEY"),
                         use_responses_api=False,
                         max_completion_tokens=8192,
                         max_retries=2,
                         stream_usage=False
                         ).with_structured_output(ProductSearch,
                                                  method="function_calling",
                                                  include_raw=True,
                                                  strict=True
                                                  )
                         
chatbot_llm = ChatOpenAI(model="gpt-5-nano",
                         temperature=0.3,
                         api_key=os.environ.get("OPENAI_API_KEY"),
                         use_responses_api=False,
                         max_completion_tokens=16384,
                         max_retries=2,
                         stream_usage=False
                         )
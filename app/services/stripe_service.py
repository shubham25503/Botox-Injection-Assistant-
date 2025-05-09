import stripe
from app.config import STRIPE_SECRET_KEY
from app.database import users_collection
stripe.api_key = STRIPE_SECRET_KEY

def fetch_products():
    try:
        prices = stripe.Price.list(
            limit=3,
            expand=["data.product"]
        )

        product_list = []
        for price in prices["data"]:
            product = price["product"]
            product_list.append({
                "product_name": product["name"],
                "description": price["nickname"],
                "price_id": price["id"],
                "amount": price["unit_amount"] / 100,
                "currency": price["currency"],
                "interval": price.get("recurring", {}).get("interval")
            })

        return product_list
    
    except stripe.error.StripeError as e:
        return {"error": f"Stripe API error: {e.user_message if hasattr(e, 'user_message') else str(e)}"}

    except Exception as e:
        return {"error": "An unexpected error occurred while fetching products."}

async def get_payment_details(data:dict):
    existing_user = await users_collection.find_one({"email": data["email"]})
    updates={"payment_status":data["is_payment_success"]}
    await users_collection.update_one(
            {"email": data["email"]},
            {"$set": updates}
        )
    
        


async def create_checkout_session(data: dict):
    try:
        email = data.get("email")
        existing_user = await users_collection.find_one({"email": email})
        price_id = data.get("price_id")
        quantity = data.get("quantity")
        success_url = data.get("success_url")
        cancel_url = data.get("cancel_url")
        print(email,existing_user)
        if not all([price_id, quantity, success_url, cancel_url]):
            raise ValueError("Missing required data fields for checkout session.")

        customer = stripe.Customer.create(
            email=email,
            name= existing_user["username"], 
            metadata={"your_user_id": str(existing_user["_id"])}
        )

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer=customer.id,
            line_items=[{
                "price": price_id,
                "quantity": quantity
            }],
            success_url=success_url,
            cancel_url=cancel_url
        )
        return {"checkout_url": session.url, "customer_id": customer.id}

    except stripe.error.CardError as e:
        return {"error": f"Card error: {e}"}

    except stripe.error.RateLimitError:
        return {"error": "Rate limit exceeded. Please try again later."}

    except stripe.error.InvalidRequestError as e:
        return {"error": f"Invalid request: {e.user_message if hasattr(e, 'user_message') else str(e)}"}

    except stripe.error.AuthenticationError:
        return {"error": "Authentication failed with Stripe."}

    except stripe.error.APIConnectionError:
        return {"error": "Network communication error with Stripe."}

    except stripe.error.StripeError as e:
        return {"error": f"An error occurred: {e.user_message if hasattr(e, 'user_message') else str(e)}"}

    except ValueError as e:
        return {"error": str(e)}

    except Exception as e:
        print(e)
        return {"error": "An unexpected error occurred while creating the checkout session."}
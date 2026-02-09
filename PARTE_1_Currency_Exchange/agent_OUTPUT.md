```
✅ ADK components imported successfully.
✅ Helper functions defined.
✅ Fee lookup function created
💳 Test: {'status': 'success', 'fee_percentage': 0.02}
✅ Exchange rate function created
💱 Test: {'status': 'success', 'rate': 0.93}
✅ Currency agent created with custom function tools
🔧 Available tools:
  • get_fee_for_payment_method - Looks up company fee structure
  • get_exchange_rate - Gets current exchange rates
```

```
### Created new session: debug_session_id

User > I want to convert 500 US Dollars to Euros using my Platinum Credit Card. How much will I receive?

currency_agent > The final amount you will receive is 455.7 Euros.

Here's the breakdown:

1.  **Fee Calculation:** A fee of 2% will be charged on 500 USD.
    *   Fee percentage: 2%
    *   Fee amount: 10 USD
    *   Amount after fee: 500 USD - 10 USD = 490 USD

2.  **Currency Conversion:** The remaining 490 USD will be converted to EUR using the exchange rate of 0.93.
    *   Exchange rate: 1 USD = 0.93 EUR
    *   Converted amount: 490 USD * 0.93 = 455.7 EUR
```

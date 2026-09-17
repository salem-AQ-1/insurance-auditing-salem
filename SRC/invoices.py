import pandas as pd

# Read Hospital 1 invoice files
invoices = pd.read_csv("invoices/hospital_1_invoices.csv")
line_items = pd.read_csv("invoices/hospital_1_line_items.csv")

# Show the columns in each file
print("Invoice columns:")
print(invoices.columns.tolist())

print("\nLine item columns:")
print(line_items.columns.tolist())

#############################
# Join invoice headers with line items using invoice_id
invoice_data = line_items.merge(
    invoices,
    on="invoice_id",
    how="left"
)
print("\nJoined columns:")
print(invoice_data.columns.tolist())
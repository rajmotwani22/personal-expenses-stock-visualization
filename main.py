from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Initialize the app
app = FastAPI()

# Directories
UPLOAD_FOLDER = "uploads"
CHARTS_FOLDER = "static/saved_charts"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHARTS_FOLDER, exist_ok=True)

# Jinja2 templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def calculate_savings_from_csv(file_path):
    """
    Reads the uploaded CSV, calculates total expenses, earnings, and savings.
    """
    try:
        data = pd.read_csv(file_path)
        data.columns = data.columns.str.strip().str.lower()

        if not {'category', 'monthlyexpense', 'earnings'}.issubset(data.columns):
            raise ValueError("CSV must contain 'Category', 'MonthlyExpense', and 'Earnings' columns.")
        
        total_expenses = data['monthlyexpense'].sum() * 12  # Annualize monthly expenses
        total_earnings = data['earnings'].sum()
        savings = total_earnings - total_expenses

        return total_expenses, total_earnings, savings, data
    except Exception as e:
        raise ValueError(f"Error processing CSV: {e}")


def visualize_investment_allocation(investment_amount, filename):
    """
    Creates and saves visualizations for investment allocation.
    """
    # Sample data for top companies
    data = {
        'Company': ['Apple', 'Amazon', 'Microsoft', 'Google', 'Tesla'],
        'Expected Return (%)': [12, 15, 10, 11, 20],
        'Risk (Volatility %)': [18, 22, 15, 17, 30]
    }
    df = pd.DataFrame(data)

    # Calculate proportional allocation
    df['Weight'] = df['Expected Return (%)'] / df['Expected Return (%)'].sum()
    df['Investment ($)'] = df['Weight'] * investment_amount

    # Create Pie Chart
    pie_path = os.path.join(CHARTS_FOLDER, f"{filename}_pie.png")
    plt.figure(figsize=(8, 6))
    plt.pie(df['Investment ($)'], labels=df['Company'], autopct='%1.1f%%', startangle=140)
    plt.title('Investment Allocation by Company')
    plt.savefig(pie_path)
    plt.close()

    # Create Bar Chart
    bar_path = os.path.join(CHARTS_FOLDER, f"{filename}_bar.png")
    plt.figure(figsize=(10, 6))
    plt.bar(df['Company'], df['Expected Return (%)'], color='skyblue')
    plt.xlabel('Company')
    plt.ylabel('Expected Return (%)')
    plt.title('Expected Returns by Company')
    plt.savefig(bar_path)
    plt.close()

    return pie_path, bar_path


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    try:
        # Save the uploaded file
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Process the file
        total_expenses, total_earnings, savings, data = calculate_savings_from_csv(file_path)

        # Generate visualizations
        if savings > 0:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            pie_path, bar_path = visualize_investment_allocation(savings, f"investment_{timestamp}")
        else:
            pie_path, bar_path = None, None

        return templates.TemplateResponse("results.html", {
            "request": request,
            "total_expenses": total_expenses,
            "total_earnings": total_earnings,
            "savings": savings,
            "pie_path": pie_path,
            "bar_path": bar_path,
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

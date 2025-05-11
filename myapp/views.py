from django.shortcuts import render
# Dashboard-view:
from django.shortcuts import render
import requests
import json
from collections import Counter
from .models import CategorySelection

API_KEY = "AIzaSyDR4jGJHp7kaHFyOJfy99hKV3UXLHvyu-c"
SHEET_ID = "1J2P_DDmpbrkTQzgykXXlr4e9winAk7yMqu7z70KFchU"

CATEGORY_RANGES = {
    'protein': 'Proteins!A1:C100',
    'genome': 'Genomes!A1:C100',
    'nucleotide': 'Nucleotide!A1:C100',
    'pubchem': 'PubChem!A1:C100',
    'taxonomy': 'Taxonomy!A1:C100',
    'blast': 'BLAST!A1:C100',
}

def fetch_sheet_data(sheet_id, range_name, api_key):
    print("fetch_sheet_data")
    print(sheet_id)
    print(range_name)
    print(api_key)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_name}?key={api_key}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def dashboard_view(request):
    category = request.GET.get('category', '').lower()
    subcategory = request.GET.get('subcategory', '').strip()
    chart_data_all = {"labels": [], "values": []}
    chart_data_top5 = {"labels": [], "values": []}
    category_totals = {}
    subcategory_set = set()

    # Calculate totals for each category
    for cat, range_name in CATEGORY_RANGES.items():
        try:
            sheet_data = fetch_sheet_data(SHEET_ID, range_name, API_KEY)
            values = sheet_data.get("values", [])
            if not values or len(values) <= 1:
                continue
            total = sum(
                float(row[2]) for row in values[1:]
                if len(row) >= 3 and row[2].replace('.', '', 1).isdigit()
            )
            category_totals[cat] = total
        except Exception as e:
            print(f"Error fetching data for {cat}: {e}")
            category_totals[cat] = 0

    # Load selected category data and prepare chart entries
    if category in CATEGORY_RANGES:
        # ✅ Log valid selection to the database
        CategorySelection.objects.create(category=category, subcategory=subcategory or None)

        try:
            sheet_data = fetch_sheet_data(SHEET_ID, CATEGORY_RANGES[category], API_KEY)
            values = sheet_data.get("values", [])
            rows = values[1:] if values and len(values) > 1 else []
            entries = []
            a = 0
            for row in rows:
                if len(row) >= 3:
                    main_cat = row[0].strip()
                    label = row[1].strip()
                    try:
                        value = float(row[2])
                    except ValueError:
                        continue

                    subcategory_set.add(main_cat)
                    if main_cat.lower() == subcategory.lower():
                        a = 1
                        entries.append((f"{label} ({main_cat})", value))
                    elif a:
                        entries.append((f"{label} ({main_cat})", value))

            if entries:
                all_labels, all_values = zip(*entries)
                chart_data_all = {"labels": all_labels, "values": all_values}

                top_entries = sorted(entries, key=lambda x: x[1], reverse=True)[:5]
                top_labels, top_values = zip(*top_entries)
                chart_data_top5 = {"labels": top_labels, "values": top_values}

        except Exception as e:
            print(f"Error processing category {category}: {e}")
            subcategory_set = set()

    return render(request, "index.html", {
        "selected_category": category,
        "selected_subcategory": subcategory,
        "chart_data_all": json.dumps(chart_data_all),
        "chart_data_top5": json.dumps(chart_data_top5),
        "categories": CATEGORY_RANGES,
        "category_totals": category_totals,
        "subcategories": sorted(subcategory_set),
    })

def show_data_view(request, category):
    category = category.lower()
    range_name = CATEGORY_RANGES.get(category)
    table_data = {'headers': [], 'rows': []}
    try:
        if not range_name:
            raise ValueError("Invalid category selected.")

        sheet_data = fetch_sheet_data(SHEET_ID, range_name, API_KEY)
        values = sheet_data.get("values", [])
        if not values or len(values) <= 1:
            raise ValueError("No data found.")

        headers = values[0]
        rows = values[1:]

        category_counts = Counter()
        current_category = None

        for row in rows:
            if len(row) >= 3:
                if row[0].strip():
                    current_category = row[0].strip()
                category_counts[current_category] += 1

        grouped_rows = []
        seen = set()
        current_category = None

        for row in rows:
            if len(row) >= 3:
                category_cell = row[0].strip() if row[0].strip() else current_category
                current_category = category_cell

                entry = {
                    "category": category_cell,
                    "name": row[1],
                    "count": row[2],
                    "show_category": category_cell not in seen,
                    "rowspan": category_counts[category_cell] if category_cell not in seen else 0
                }

                if entry["show_category"]:
                    seen.add(category_cell)

                grouped_rows.append(entry)

        table_data = {
            'headers': headers,
            'rows': grouped_rows
        }

    except Exception as e:
        print("Error in show_data_view:", str(e))

    return render(request, "show_data.html", {
        "category": category,
        "table_data": table_data
    })



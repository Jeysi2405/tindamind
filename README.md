# TindaMind

Machine Learning-Based Sales Analytics and Predictive Inventory Management System for Local Micro-Retailers.

---

## Academic Information
* **Subject:** Application Development and Emerging Technologies (APPDEV)
* **Section:** BSCS 3A
* **Instructor:** Prof. Jefferson Costales

---

## Development Team
* **James Christian Huelar** – Project Lead / Scrum Master
* **Nicole Achay** – Front-End Developer / UI-UX Developer
* **Dimple Adel Barrun** – Back-End Developer
* **Nydia Elveña** – Emerging Technology / QA Lead

---

## Project Overview

### Description
TindaMind is a lightweight, mobile-responsive web application designed to integrate a Point-of-Sale (POS) terminal, inventory management, and predictive sales analytics.

### Why This Project Was Chosen
Micro, Small, and Medium Enterprises (MSMEs) make up 99.6% of all businesses in the Philippines and generate over 65% of national employment. Despite their importance, community micro-retailers such as neighborhood sari-sari stores, bakeries, and mini-groceries face a widening digital divide and lack access to practical digital tools.

Most micro-retailers continue to rely on manual paper notebooks or intuition to track stock and sales:
* **Stockouts:** Unpredicted demand spikes deplete fast-moving items, causing immediate lost revenue.
* **Overstocking and Spoilage:** Purchasing excess inventory traps critical working capital and leads to product spoilage.
* **Enterprise ERP Barriers:** Existing commercial ERP platforms are bloated, complicated, and too costly for micro-businesses.

TindaMind was conceptualized to address these challenges with a simple, affordable web solution. By replacing manual guesswork with machine learning models that analyze rolling sales velocity and predict 7-day demand spikes, the system helps micro-retailers keep fast-moving items accessible, cut spoilage, and save operational time.

---

## Technology Stack
* **Backend:** Python 3.12, Flask, Flask-SQLAlchemy, Flask-Login, Flask-Bcrypt
* **Frontend:** Jinja2, Tailwind CSS, Chart.js
* **Database:** SQLite (development), PostgreSQL (production)
* **Emerging Technology:** Scikit-learn (Linear Regression / Ridge Regression)
* **Deployment Platform:** Render

---

## Core System Modules
1. **Point-of-Sale (POS) Terminal:** Search items by product name, shopping cart processing, checkout, automatic inventory deduction, transaction recording, and receipt generation.
2. **Inventory & Stock Tracking:** Item catalog management, category organization, inventory threshold alerts, and cost/retail price tracking.
3. **Suppliers & Automated Restocking:** Supplier directory records, restocking recommendations, and stockout-risk purchase order generation.
4. **Sales Analytics:** Transaction auditing, daily sales summaries, and product performance analytics.
5. **Machine Learning Forecasting:** 7-day rolling demand predictions and stockout-risk classification (High, Moderate, Low).
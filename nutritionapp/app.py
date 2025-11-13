import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import math
import pandas as pd
from datetime import date

# --- Page Configuration ---
st.set_page_config(
    page_title="Personalized Nutrition Calculator",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GLOBAL CONSTANTS ---

# Simplified Goal Adjustments for Calorie Deficit/Surplus
GOAL_ADJUSTMENTS = {
    "Maintain Current Weight": 0,
    "Lose 0.5 lb / week (Gentle Deficit)": -250,
    "Lose 1.0 lb / week (Standard Deficit)": -500,
    "Gain 0.5 lb / week (Lean Surplus)": 250,
    "Gain 1.0 lb / week (Standard Surplus)": 500,
}

# Standard Macro Ratios (Carbs, Protein, Fat)
MACRO_PRESETS = {
    "Balanced (40/30/30)": (0.40, 0.30, 0.30),
    "High Protein (30/40/30)": (0.30, 0.40, 0.30),
    "Lower Carb (35/30/35)": (0.35, 0.30, 0.35),
    "High Carb / Low Fat (50/30/20)": (0.50, 0.30, 0.20)
}

MET_VALUES = {
    "Select an activity...": 0.0,
    "Running (Slow, 10 min/mile)": 9.8,
    "Running (Fast, 7 min/mile)": 12.8,
    "Cycling (Moderate, 12-14 mph)": 8.0,
    "Weightlifting (Vigorous)": 6.0,
    "Walking (Brisk, 3.5 mph)": 3.8,
    "Yoga": 2.5,
    "Swimming (Moderate)": 7.0
}

# --- Custom CSS for Aesthetics (Dark Mode UI) ---
st.markdown("""
<style>
/* Streamlit's main content area background */
.stApp {
    background-color: #121212; /* Deep dark background */
    color: #ffffff; /* White text for contrast */
}

/* Metric Cards for Key Metrics */
.metric-card {
    background-color: #1e1e1e; /* Slightly lighter dark for cards */
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4); /* Darker shadow */
    border: 1px solid #333333; /* Darker border */
    transition: all 0.3s;
}
.metric-card:hover {
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.6);
    transform: translateY(-2px);
}

/* Customizing Streamlit Metrics for larger font */
[data-testid="stMetric"] label {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: #B0B0B0 !important; /* Light gray for labels */
}
[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    color: #00BFFF !important; /* Bright blue for general values */
}

/* Adjusting custom metric card colors for dark mode visibility */
.metric-card div[style*="color: #DC3545;"] { color: #FF6B6B !important; } /* Calorie (Reddish) */
.metric-card div[style*="color: #007BFF;"] { color: #5B9ADF !important; } /* Protein (Blue) */
.metric-card div[style*="color: #17A2B8;"] { color: #40E0D0 !important; } /* Water (Cyan) */
.metric-card div[style*="color: #28A745;"] { color: #8FBC8F !important; } /* BMI (Green) */

/* Specific card style adjustments */
.metric-card[style*="border-left: 5px solid #28A745;"] { border-left-color: #8FBC8F !important; } /* Timeline border */
.metric-card[style*="background-color: #f0f8ff;"] { background-color: #2a2a2a !important; } /* Exercise card background */
.metric-card[style*="border-left: 5px solid #007bff;"] { border-left-color: #00BFFF !important; } /* Exercise card border */

</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---

def calculate_bmr(weight_kg, height_cm, age, sex):
    """Calculate Basal Metabolic Rate (BMR) using the Mifflin-St Jeor equation."""
    if sex == "Male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:  # Female
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    return bmr


def get_tdee(bmr, activity_level):
    """Calculate Total Daily Energy Expenditure (TDEE)."""
    activity_multipliers = {
        "Sedentary (little or no exercise)": 1.2,
        "Lightly Active (light exercise/sports 1-3 days/week)": 1.375,
        "Moderately Active (moderate exercise/sports 3-5 days/week)": 1.55,
        "Very Active (hard exercise/sports 6-7 days a week)": 1.725,
        "Extra Active (very hard exercise/sports & physical job)": 1.9
    }
    return bmr * activity_multipliers[activity_level]


def get_macros(tdee, calorie_adjustment, macro_ratio_preset):
    """Calculate target calories and macros based on TDEE, adjustment, and ratio preset."""
    target_calories = tdee + calorie_adjustment

    # Enforce minimum healthy calorie intake
    if target_calories < 1200:
        target_calories = 1200

    c_ratio, p_ratio, f_ratio = MACRO_PRESETS[macro_ratio_preset]  # Carbs, Protein, Fat

    # Calculate Calories for each macro
    protein_cal = target_calories * p_ratio
    carb_cal = target_calories * c_ratio
    fat_cal = target_calories * f_ratio

    # Convert Calories to Grams
    protein_g = protein_cal / 4
    carb_g = carb_cal / 4
    fat_g = fat_cal / 9

    macros = {
        "calories": target_calories,
        "protein_g": protein_g, "protein_cal": protein_cal,
        "fat_g": fat_g, "fat_cal": fat_cal,
        "carbs_g": carb_g, "carbs_cal": carb_cal
    }
    return {k: round(v, 1) for k, v in macros.items()}


def calculate_water_intake(weight_kg):
    """Calculate recommended daily water intake (Liters) based on weight."""
    return round((weight_kg * 35) / 1000, 1)


def calculate_bmi(weight_kg, height_cm):
    """Calculate Body Mass Index (BMI) and category."""
    if height_cm <= 0: return 0, "N/A"
    bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)

    if bmi < 18.5:
        category = "Underweight"
    elif 18.5 <= bmi < 25:
        category = "Healthy Weight"
    elif 25 <= bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    return bmi, category


def calculate_goal_timeline(current_weight_kg, target_weight_kg, daily_calorie_deficit):
    """Estimate the weeks required to reach a target weight."""
    if daily_calorie_deficit <= 0: return 0
    KCAL_PER_KG_FAT = 7700  # Approximate energy content of 1 kg of body fat
    total_kg_to_lose = current_weight_kg - target_weight_kg

    if total_kg_to_lose <= 0: return 0

    total_calorie_deficit_needed = total_kg_to_lose * KCAL_PER_KG_FAT
    total_days = total_calorie_deficit_needed / daily_calorie_deficit
    return math.ceil(total_days / 7)


# --- Main App Interface ---
st.title("🍎 Personalized Nutrition Dashboard")
st.markdown(
    "Calculate your daily needs and macro targets based on **science and fixed, reliable ratios**.")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("🏋️‍♂️ Your Body Metrics")

    # --- Unit Selection ---
    unit_system = st.radio("**Unit System**", ("Metric (kg, cm)", "Imperial (lbs, ft/in)"))

    weight = 0.0
    weight_lbs = 0.0

    # --- Conditional Inputs based on Unit System ---
    if unit_system == "Metric (kg, cm)":
        weight = st.number_input("Weight (kg)", min_value=1.0, value=70.0, step=0.1)
        height = st.number_input("Height (cm)", min_value=1.0, value=170.0, step=0.1)
        weight_kg = weight
        height_cm = height
    else:  # Imperial
        weight_lbs = st.number_input("Weight (lbs)", min_value=1.0, value=154.0, step=0.1)
        col_ft, col_in = st.columns(2)
        height_ft = col_ft.number_input("Height (ft)", min_value=0, value=5)
        height_in = col_in.number_input("Height (in)", min_value=0, max_value=11, value=7)

        # Convert to metric for calculations
        weight_kg = weight_lbs * 0.453592
        height_cm = (height_ft * 30.48) + (height_in * 2.54)

    age = st.number_input("Age", min_value=1, max_value=120, value=25)
    sex = st.selectbox("Sex", ("Male", "Female"))

    activity_level = st.selectbox(
        "Activity Level",
        (
            "Sedentary (little or no exercise)",
            "Lightly Active (light exercise/sports 1-3 days/week)",
            "Moderately Active (moderate exercise/sports 3-5 days/week)",
            "Very Active (hard exercise/sports 6-7 days a week)",
            "Extra Active (very hard exercise/sports & physical job)"
        )
    )

    st.header("🎯 Goal Settings")

    # Goal Adjustment Selector
    goal_string = st.selectbox(
        "Desired Weekly Weight Change",
        list(GOAL_ADJUSTMENTS.keys()),
        key='current_goal_string',
        help="This sets your daily calorie surplus or deficit."
    )
    calorie_adjustment = GOAL_ADJUSTMENTS[goal_string]

    # Macro Ratio Selector
    macro_ratio = st.selectbox(
        "Macro Ratio Preset (C/P/F)",
        list(MACRO_PRESETS.keys()),
        key='current_macro_ratio',
        help="Select a ratio to define your split of Carbs, Protein, and Fats."
    )

    target_weight_input = 0.0
    if "Lose" in goal_string:
        default_val_kg = round(weight_kg * 0.9, 1)
        default_val_units = default_val_kg if unit_system == "Metric (kg, cm)" else round(default_val_kg / 0.453592, 1)

        target_weight_input = st.number_input(
            f"Optional: Target Weight ({'kg' if unit_system == 'Metric (kg, cm)' else 'lbs'})",
            min_value=0.0,
            value=default_val_units,
            step=0.1,
            help="Set a lower target weight to estimate your timeline."
        )

    st.markdown("---")
    calculate_button = st.button("Calculate My Plan", type="primary", use_container_width=True)

# --- Results Area ---
if not calculate_button:
    st.info("👈 Fill in your details and click 'Calculate My Plan' in the sidebar to see your personalized dashboard.")
else:
    # --- 1. Perform All Calculations (if inputs are valid) ---
    if weight_kg <= 0 or height_cm <= 0 or age <= 0:
        st.error("Please enter valid (positive) numbers for weight, height, and age.")
        st.stop()

    bmr = calculate_bmr(weight_kg, height_cm, age, sex)
    tdee = get_tdee(bmr, activity_level)
    macros = get_macros(tdee, calorie_adjustment, macro_ratio)
    water_liters = calculate_water_intake(weight_kg)
    bmi, bmi_category = calculate_bmi(weight_kg, height_cm)

    timeline_weeks = 0
    target_weight_kg = 0
    if "Lose" in goal_string and target_weight_input > 0:
        target_weight_kg = target_weight_input if unit_system == "Metric (kg, cm)" else target_weight_input * 0.453592
        if target_weight_kg < weight_kg:
            timeline_weeks = calculate_goal_timeline(weight_kg, target_weight_kg, abs(calorie_adjustment))

    # --- 2. Create UI with Tabs ---
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Macros", "🔬 Calorie Science & Timeline", "🏃‍♂️ Exercise Tools"])

    # --- TAB 1: DASHBOARD & MACROS ---
    with tab1:
        st.success(f"Plan calculated for goal: **{goal_string}**")
        st.header("Key Daily Targets")

        col1, col2, col3, col4 = st.columns(4)

        # Displaying key metrics with the custom style
        with col1:
            st.markdown(
                f'<div class="metric-card">Target Calories<div style="font-size: 2rem; font-weight: 800; color: #FF6B6B;">{math.floor(macros["calories"])} kcal</div><p style="font-size: 0.9rem; color: #999999;">{calorie_adjustment:+d} kcal Adjustment</p></div>',
                unsafe_allow_html=True)

        with col2:
            st.markdown(
                f'<div class="metric-card">Protein Target<div style="font-size: 2rem; font-weight: 800; color: #5B9ADF;">{math.floor(macros["protein_g"])} g</div><p style="font-size: 0.9rem; color: #999999;">{MACRO_PRESETS[macro_ratio][1] * 100}% of Calories</p></div>',
                unsafe_allow_html=True)

        with col3:
            st.markdown(
                f'<div class="metric-card">Water Intake<div style="font-size: 2rem; font-weight: 800; color: #40E0D0;">{water_liters} L</div><p style="font-size: 0.9rem; color: #999999;">Hydration Goal</p></div>',
                unsafe_allow_html=True)

        with col4:
            st.markdown(
                f'<div class="metric-card">BMI<div style="font-size: 2rem; font-weight: 800; color: #8FBC8F;">{bmi}</div><p style="font-size: 0.9rem; color: #999999;">{bmi_category}</p></div>',
                unsafe_allow_html=True)

        st.markdown("---")

        # Macro Breakdown (Chart and Table)
        st.header("Macronutrient Breakdown")
        col_chart, col_details = st.columns([1, 1.2])

        with col_chart:
            st.subheader("Calorie Distribution")

            # Donut Chart for Macros
            labels = ['Carbohydrates', 'Protein', 'Fats']
            values = [macros['carbs_cal'], macros['protein_cal'], macros['fat_cal']]
            # Adjusted colors for better visibility on a dark background
            colors = ['#40E0D0', '#FF6B6B', '#FFD700']

            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=.4,
                marker_colors=colors,
                textinfo='percent',
                hovertemplate='%{label}: <b>%{value:.0f} kcal</b><extra></extra>',
            )])

            c_ratio, p_ratio, f_ratio = MACRO_PRESETS[macro_ratio]
            ratio_display = f"{int(c_ratio * 100)}/{int(p_ratio * 100)}/{int(f_ratio * 100)}"
            fig.add_annotation(
                text=ratio_display,
                x=0.5, y=0.5, font_size=24, showarrow=False, font_color="#D3D3D3"  # Light gray for annotation
            )

            # Update layout for dark mode background
            fig.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5,
                            font=dict(color="#ffffff")),
                height=350,
                plot_bgcolor='#121212',
                paper_bgcolor='#121212',
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_details:
            st.subheader("Detailed Grams & Calorie Split")

            # Prepare data for a clean table display
            data = {
                'Nutrient': ['Protein', 'Carbohydrates', 'Fats'],
                'Grams (g)': [macros['protein_g'], macros['carbs_g'], macros['fat_g']],
                'Calories (kcal)': [macros['protein_cal'], macros['carbs_cal'], macros['fat_cal']],
                'Calorie %': [
                    round(macros['protein_cal'] / macros['calories'] * 100, 1),
                    round(macros['carbs_cal'] / macros['calories'] * 100, 1),
                    round(macros['fat_cal'] / macros['calories'] * 100, 1)
                ]
            }
            df = pd.DataFrame(data).round(1)

            st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Grams (g)": st.column_config.NumberColumn("Grams (g)", format="%.1f"),
                    "Calories (kcal)": st.column_config.NumberColumn("Calories (kcal)", format="%.0f"),
                    # Use a light progress bar color for dark mode
                    "Calorie %": st.column_config.ProgressColumn("Calorie %", format="%.1f %%", min_value=0,
                                                                 max_value=100, color="#00BFFF"),
                }
            )

    # --- TAB 2: CALORIE SCIENCE & TIMELINE ---
    with tab2:
        st.header("🔬 The Science Behind Your Calories")
        st.info(
            "Understanding your Basal Metabolic Rate (BMR) and Total Daily Energy Expenditure (TDEE) is essential for any goal.")

        # Display BMR vs TDEE with a progress bar style
        st.subheader("Maintenance vs. Target")

        # Determine the maximum value for the bar chart
        max_cal = max(macros['calories'], tdee, 2500)

        st.markdown(f"**Basal Metabolic Rate (BMR):** Energy burned at complete rest.")
        st.progress(bmr / max_cal, text=f"**{round(bmr, 0):.0f} kcal**")

        st.markdown(
            f"**Total Daily Energy Expenditure (TDEE):** Energy burned including activity (Your Maintenance Calories).")
        st.progress(tdee / max_cal, text=f"**{round(tdee, 0):.0f} kcal**")

        st.markdown(f"**Target Calories:** TDEE adjusted by {calorie_adjustment:+d} kcal for your goal.")
        st.progress(macros['calories'] / max_cal, text=f"**{math.floor(macros['calories'])} kcal**")

        # --- Timeline Feature ---
        if timeline_weeks > 0:
            st.markdown("---")
            st.header("📅 Estimated Goal Timeline")

            # Metric Card for Timeline
            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid #8FBC8F;">
                <p style="font-size: 1.1rem; color: #B0B0B0; margin-bottom: 5px;">
                    Time to reach **{target_weight_kg:.1f} kg**
                </p>
                <div style="font-size: 2.5rem; font-weight: 700; color: #8FBC8F;">
                    {timeline_weeks} Weeks
                </div>
                <p style="font-size: 0.9rem; color: #6C757D;">
                    Based on your **{abs(calorie_adjustment)} kcal daily deficit**.
                </p>
            </div>
            """, unsafe_allow_html=True)
        elif "Lose" in goal_string and target_weight_input > 0 and target_weight_kg >= weight_kg:
            st.warning("Your target weight must be lower than your current weight to calculate a timeline.")

    # --- TAB 3: EXERCISE TOOLS ---
    with tab3:
        st.header("🏃‍♂️ Exercise Calorie Estimator")
        st.markdown(
            f"Use your **current weight ({weight_kg:.1f} kg)** and the Metabolic Equivalent of Task (MET) values to estimate calories burned.")

        col_act, col_dur, col_burn = st.columns([2, 1, 1])

        with col_act:
            activity = st.selectbox("Select Activity:", options=list(MET_VALUES.keys()), key='activity_select')
        with col_dur:
            duration = st.number_input("Duration (minutes):", min_value=1, value=30, key='duration_input')

        if activity != "Select an activity...":
            met = MET_VALUES.get(activity, 0.0)
            duration_hours = duration / 60.0
            calories_burned = math.floor(met * weight_kg * duration_hours)

            with col_burn:
                st.markdown(f"""
                <div class="metric-card" style="background-color: #2a2a2a; border-left: 5px solid #00BFFF;">
                    <p style="font-size: 1rem; color: #B0B0B0; margin-bottom: 5px;">
                        Est. Calories Burned
                    </p>
                    <div style="font-size: 2rem; font-weight: 700; color: #00BFFF;">
                        {calories_burned} kcal
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <small>Calculation: MET value of **{met}** x Weight in kg ({weight_kg:.1f}) x Duration in hours ({duration_hours:.2f})</small>
            """)
        else:
            st.info("Select an activity to calculate estimated calories burned.")

    st.markdown("---")
    st.warning(
        "**Disclaimer:** This calculator provides estimates based on scientific formulas and generalized MET values. It is not medical or professional dietetic advice. Consult a healthcare professional before making significant changes to your diet or fitness routine.",
        icon="⚠️")
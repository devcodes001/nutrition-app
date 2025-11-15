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


def get_macros(tdee, macro_ratio_preset):
    """Calculate target calories and macros based on TDEE and ratio preset.
    Target calories = TDEE (Maintenance)."""
    target_calories = tdee

    # Enforce minimum healthy calorie intake (though TDEE usually covers this)
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


# --- Session State Initialization ---
if 'calculated' not in st.session_state:
    st.session_state.calculated = False
    st.session_state.results = {}
    st.session_state.weight_kg = 70.0  # Default for exercise tool
    st.session_state.macro_ratio = "Balanced (40/30/30)"  # Default macro ratio


def run_calculation():
    """Calculates all metrics and stores them in session state."""
    # Retrieve base inputs from sidebar widgets
    weight_kg = st.session_state.get('weight_kg_sidebar', 0.0)
    height_cm = st.session_state.get('height_cm_sidebar', 0.0)
    age = st.session_state.get('age_sidebar', 0)
    sex = st.session_state.get('sex_sidebar', 'Male')
    activity_level = st.session_state.get('activity_sidebar', 'Sedentary (little or no exercise)')

    # Retrieve macro ratio from session state (updated by sidebar or dashboard widget)
    macro_ratio = st.session_state.macro_ratio

    if weight_kg <= 0 or height_cm <= 0 or age <= 0:
        # st.error("Please enter valid (positive) numbers for weight, height, and age.") # Keep this check silent as it blocks the first render
        st.session_state.calculated = False
        return

    bmr = calculate_bmr(weight_kg, height_cm, age, sex)
    tdee = get_tdee(bmr, activity_level)
    macros = get_macros(tdee, macro_ratio)
    water_liters = calculate_water_intake(weight_kg)
    bmi, bmi_category = calculate_bmi(weight_kg, height_cm)

    # Store results in session state
    st.session_state.calculated = True
    st.session_state.results = {
        "bmr": bmr, "tdee": tdee, "macros": macros, "water_liters": water_liters,
        "bmi": bmi, "bmi_category": bmi_category,
        "weight_kg": weight_kg, "macro_ratio": macro_ratio
    }
    st.session_state.weight_kg = weight_kg  # Update weight for exercise tool fallback


# FIX: New/Modified callback function for immediate dashboard update
def update_macro_and_recalculate():
    """Callback to update the main macro ratio and rerun all calculations."""
    # The selectbox (key='macro_ratio_dashboard') value is already updated
    # We explicitly update the main state variable which run_calculation uses
    st.session_state.macro_ratio = st.session_state.macro_ratio_dashboard

    # Rerun the calculation
    run_calculation()


# --- Main App Interface ---
st.title("🍎 Personalized Nutrition Dashboard (Maintenance Focus)")
st.markdown(
    "Calculate your **Maintenance** daily calorie needs and macro targets based on **science and fixed, reliable ratios**.")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("🏋️‍♂️ Your Body Metrics")

    # --- Unit Selection ---
    unit_system = st.radio("**Unit System**", ("Metric (kg, cm)", "Imperial (lbs, ft/in)"))

    weight_kg = 0.0
    height_cm = 0.0

    # --- Conditional Inputs based on Unit System ---
    if unit_system == "Metric (kg, cm)":
        weight = st.number_input("Weight (kg)", min_value=1.0, value=70.0, step=0.1, key='weight_kg_sidebar')
        height = st.number_input("Height (cm)", min_value=1.0, value=170.0, step=0.1, key='height_cm_sidebar')
        weight_kg = weight
        height_cm = height
    else:  # Imperial
        weight_lbs = st.number_input("Weight (lbs)", min_value=1.0, value=154.0, step=0.1, key='weight_lbs_sidebar')
        col_ft, col_in = st.columns(2)
        height_ft = col_ft.number_input("Height (ft)", min_value=0, value=5, key='height_ft_sidebar')
        height_in = col_in.number_input("Height (in)", min_value=0, max_value=11, value=7, key='height_in_sidebar')

        # Convert to metric for calculations
        weight_kg = weight_lbs * 0.453592
        height_cm = (height_ft * 30.48) + (height_in * 2.54)

        # Store for use in run_calculation callback
        st.session_state['weight_kg_sidebar'] = weight_kg
        st.session_state['height_cm_sidebar'] = height_cm

    age = st.number_input("Age", min_value=1, max_value=120, value=25, key='age_sidebar')
    sex = st.selectbox("Sex", ("Male", "Female"), key='sex_sidebar')

    activity_level = st.selectbox(
        "Activity Level",
        (
            "Sedentary (little or no exercise)",
            "Lightly Active (light exercise/sports 1-3 days/week)",
            "Moderately Active (moderate exercise/sports 3-5 days/week)",
            "Very Active (hard exercise/sports 6-7 days a week)",
            "Extra Active (very hard exercise/sports & physical job)"
        ),
        key='activity_sidebar'
    )

    st.header("⚙️ Initial Macro Setting")

    # Macro Ratio Selector (Initial Setting - Stored in session_state.macro_ratio)
    macro_ratio_initial = st.selectbox(
        "Macro Ratio Preset (C/P/F)",
        list(MACRO_PRESETS.keys()),
        key='macro_ratio',  # Updates st.session_state.macro_ratio
        help="Select a ratio to define your split of Carbs, Protein, and Fats."
    )

    st.markdown("---")

    st.button("Calculate My Plan", on_click=run_calculation, type="primary", use_container_width=True)

# --- Tabs Structure (Always visible) ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Macros", "🔬 Calorie Science", "🏃‍♂️ Exercise Tools"])

# --- TAB 1: DASHBOARD & MACROS ---
with tab1:
    if not st.session_state.calculated:
        st.info(
            "👈 Fill in your details and click 'Calculate My Plan' in the sidebar to see your personalized dashboard.")
    else:
        # Retrieve results from session state
        res = st.session_state.results
        macros = res['macros']
        water_liters = res['water_liters']
        bmi = res['bmi']
        bmi_category = res['bmi_category']
        macro_ratio = res['macro_ratio']
        target_calories = math.floor(macros["calories"])

        st.success(f"Plan calculated for goal: **Maintain Current Weight** using {macro_ratio} ratio.")

        # --- NEW FEATURE: Macro Adjustment on Dashboard ---
        st.header("🎯 Adjust Macro Ratio")
        col_macro = st.columns(1)[0]  # Changed from 2 columns to 1 to simplify after removing button

        with col_macro:
            # Macro Ratio Selector (Dashboard Setting) - FIXED with on_change
            st.selectbox(
                "Change Macro Ratio Preset (C/P/F):",
                list(MACRO_PRESETS.keys()),
                index=list(MACRO_PRESETS.keys()).index(st.session_state.macro_ratio),
                key='macro_ratio_dashboard',  # Stores new value here
                on_change=update_macro_and_recalculate,  # IMMEDIATE RE-CALCULATION
                help="Change the ratio to instantly update your targets below."
            )
            # st.session_state.macro_ratio = st.session_state.macro_ratio_dashboard # REMOVED: Handled by callback

        st.markdown("---")
        # --- END NEW FEATURE ---

        st.header("Key Daily Targets")

        col1, col2, col3, col4 = st.columns(4)

        # Displaying key metrics with the custom style
        with col1:
            st.markdown(
                f'<div class="metric-card">Target Calories<div style="font-size: 2rem; font-weight: 800; color: #FF6B6B;">{target_calories} kcal</div><p style="font-size: 0.9rem; color: #999999;">Maintenance Level (TDEE)</p></div>',
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

        # --- DUMMY DIET PLAN FEATURE ---
        st.markdown("---")
        st.header("🍽️ Suggested Meal Distribution (Dummy Plan)")
        st.warning(
            "This is a simple template to distribute your macros. Food choices must be made by the user to meet these targets.")

        # Define the macro split across meals (e.g., 25/40/35 for Calories)
        MEAL_SPLIT = {
            "Breakfast": 0.25,  # 25%
            "Lunch": 0.40,  # 40%
            "Dinner": 0.35  # 35%
        }

        meal_data = []
        for meal, ratio in MEAL_SPLIT.items():
            meal_macros = {
                "Meal": meal,
                "Est. Calories (kcal)": math.floor(target_calories * ratio),
                "Protein (g)": round(macros['protein_g'] * ratio, 1),
                "Carbs (g)": round(macros['carbs_g'] * ratio, 1),
                "Fats (g)": round(macros['fat_g'] * ratio, 1)
            }
            meal_data.append(meal_macros)

        df_meals = pd.DataFrame(meal_data)

        st.dataframe(
            df_meals,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Est. Calories (kcal)": st.column_config.NumberColumn("Est. Calories (kcal)", format="%.0f"),
                "Protein (g)": st.column_config.NumberColumn("Protein (g)", format="%.1f"),
                "Carbs (g)": st.column_config.NumberColumn("Carbs (g)", format="%.1f"),
                "Fats (g)": st.column_config.NumberColumn("Fats (g)", format="%.1f"),
            }
        )

        st.caption(
            f"Total Daily Macros: {math.floor(macros['protein_g'])}g Protein, {math.floor(macros['carbs_g'])}g Carbs, {math.floor(macros['fat_g'])}g Fats.")
        # --- END DUMMY DIET PLAN FEATURE ---

# --- TAB 2: CALORIE SCIENCE ---
with tab2:
    if not st.session_state.calculated:
        st.info("👈 Please calculate your plan in the sidebar to view your calorie science details.")
    else:
        res = st.session_state.results
        bmr = res['bmr']
        tdee = res['tdee']
        macros = res['macros']

        st.header("🔬 The Science Behind Your Calories")
        st.info(
            "Understanding your Basal Metabolic Rate (BMR) and Total Daily Energy Expenditure (TDEE) is essential for your maintenance calories.")

        # Display BMR vs TDEE with a progress bar style
        st.subheader("BMR vs. TDEE")

        # Determine the maximum value for the bar chart
        max_cal = max(macros['calories'], tdee, 2500)

        st.markdown(f"**Basal Metabolic Rate (BMR):** Energy burned at complete rest.")
        st.progress(bmr / max_cal, text=f"**{round(bmr, 0):.0f} kcal**")

        st.markdown(
            f"**Total Daily Energy Expenditure (TDEE):** Energy burned including activity (Your Maintenance Calories).")
        st.progress(tdee / max_cal, text=f"**{round(tdee, 0):.0f} kcal**")

        st.markdown(f"**Target Calories:** This is equal to your TDEE for maintenance.")
        st.progress(macros['calories'] / max_cal, text=f"**{math.floor(macros['calories'])} kcal**")

# --- TAB 3: EXERCISE TOOLS ---
with tab3:
    # Use the weight from the sidebar (current_weight_kg)
    current_weight_kg = st.session_state.get('weight_kg_sidebar', 70.0)

    st.header("🏃‍♂️ Exercise Calorie Estimator")
    st.markdown(
        f"Use your **current weight ({current_weight_kg:.1f} kg)** and the Metabolic Equivalent of Task (MET) values to estimate calories burned.")

    col_act, col_dur, col_burn = st.columns([2, 1, 1])

    with col_act:
        activity = st.selectbox("Select Activity:", options=list(MET_VALUES.keys()), key='activity_select_tab3')
    with col_dur:
        duration = st.number_input("Duration (minutes):", min_value=1, value=30, key='duration_input_tab3')

    if activity != "Select an activity...":
        met = MET_VALUES.get(activity, 0.0)
        duration_hours = duration / 60.0
        calories_burned = math.floor(met * current_weight_kg * duration_hours)

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
        <small>Calculation: MET value of **{met}** x Weight in kg ({current_weight_kg:.1f}) x Duration in hours ({duration_hours:.2f})</small>
        """)
    else:
        st.info("Select an activity to calculate estimated calories burned.")

st.markdown("---")
st.warning(
    "**Disclaimer:** This calculator provides estimates based on scientific formulas and generalized MET values. It is not medical or professional dietetic advice. Consult a healthcare professional before making significant changes to your diet or fitness routine.",
    icon="⚠️")

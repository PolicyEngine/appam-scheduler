"""
Calculate booth value based on time of day and number of people.
Booth traffic varies throughout the day.
"""
from datetime import datetime


def parse_time(time_str):
    """Parse time string to hour."""
    try:
        match = time_str.match(/(\d+):(\d+)(am|pm)/i)
        if not match:
            return 12
        hours = int(match.group(1))
        period = match.group(3).lower()
        if period == 'pm' and hours != 12:
            hours += 12
        if period == 'am' and hours == 12:
            hours = 0
        return hours
    except:
        return 12


def get_booth_traffic_multiplier(date, start_time):
    """
    Get traffic multiplier for booth at this time.

    Returns multiplier (0.5 to 2.0):
    - High traffic times: 2.0x (morning arrival, lunch, late afternoon)
    - Medium traffic: 1.0x (mid-morning, mid-afternoon)
    - Low traffic: 0.5x (early morning, evening)
    """
    try:
        hour = int(start_time.replace('am', '').replace('pm', '').split(':')[0])
        is_pm = 'pm' in start_time.lower()

        if not is_pm and hour != 12:
            actual_hour = hour
        elif is_pm and hour != 12:
            actual_hour = hour + 12
        elif hour == 12 and is_pm:
            actual_hour = 12
        else:
            actual_hour = 0

        # High traffic periods
        if 8 <= actual_hour <= 9:  # Morning arrival
            return 2.0
        elif 12 <= actual_hour <= 13:  # Lunch time
            return 2.5  # PEAK - people browsing
        elif 15 <= actual_hour <= 17:  # Late afternoon
            return 1.8

        # Medium traffic
        elif 10 <= actual_hour <= 11:  # Mid-morning
            return 1.2
        elif 14 <= actual_hour <= 15:  # Mid-afternoon
            return 1.2

        # Low traffic
        elif actual_hour < 8:  # Very early
            return 0.3
        elif actual_hour >= 18:  # Evening
            return 0.5

        return 1.0

    except:
        return 1.0


def calculate_booth_value(num_people_at_booth, date, start_time):
    """
    Calculate total booth value considering:
    1. Number of people (diminishing returns)
    2. Time of day (traffic patterns)

    Returns: booth value score
    """
    # Base value by staffing level
    base_values = {
        0: -1000,  # NEVER acceptable
        1: 100,    # Baseline - requirement met
        2: 150,    # Good coverage - can handle multiple visitors
        3: 160     # Minimal additional value
    }

    if num_people_at_booth not in base_values:
        return -1000

    base_value = base_values[num_people_at_booth]

    # Apply traffic multiplier
    traffic_mult = get_booth_traffic_multiplier(date, start_time)

    # For 0 people, always unacceptable regardless of traffic
    if num_people_at_booth == 0:
        return -1000

    # For 1 person during high traffic, value is actually higher (worth keeping 2)
    # For 1 person during low traffic, value is fine
    adjusted_value = base_value * traffic_mult

    return adjusted_value


# Example calculations
if __name__ == '__main__':
    print("BOOTH VALUE EXAMPLES")
    print("="*80)
    print()

    test_scenarios = [
        ("2025-11-13", "8:30am", "Morning arrival - HIGH traffic"),
        ("2025-11-13", "10:15am", "Mid-morning - MEDIUM traffic"),
        ("2025-11-13", "12:00pm", "Lunch - PEAK traffic"),
        ("2025-11-13", "1:45pm", "Early afternoon - MEDIUM traffic"),
        ("2025-11-13", "3:30pm", "Late afternoon - HIGH traffic"),
        ("2025-11-13", "6:30pm", "Evening - LOW traffic"),
    ]

    for date, time, description in test_scenarios:
        print(f"{description} ({time}):")
        for num_people in [0, 1, 2, 3]:
            value = calculate_booth_value(num_people, date, time)
            print(f"  {num_people} people at booth: {value:>6.0f} value")
        print()

    print("\nKEY INSIGHTS:")
    print("- Lunch time (12pm): Keep 2 people at booth if possible (375 value)")
    print("- Morning (8:30am): Keep 2 people at booth (300 value)")
    print("- Low traffic (6:30pm): 1 person fine (50 value)")
    print("- NEVER leave booth empty: -1000 penalty")

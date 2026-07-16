def print_comparison_table():
    """Print the comparison data in a nice table format"""
    
    # Your data
    data = [
        ["Acacia", "Very High", 30.00, "Low", 89.17, 8.24, 0],
        ["Baritan", "Low", 30.00, "Low", 89.14, 0.80, 0],
        ["Bayan-Bayanan", "Low", 30.00, "Low", 88.19, 0.46, 0],
        ["Catmon", "Very High", 30.00, "Moderate", 93.00, 38.48, 2],
        ["Concepcion", "Low", 30.00, "Low", 90.14, 0.00, 0],
        ["Dampalit", "Moderate", 30.00, "Low", 87.20, 4.75, 0],
        ["Flores", "Very High", 30.00, "Low", 87.74, 8.16, 0],
        ["Hulong Duhat", "Very High", 33.57, "Moderate", 94.22, 35.92, 3],
        ["Ibaba", "Low", 30.00, "Low", 88.72, 0.89, 1],
        ["Longos", "Low", 40.01, "High", 91.71, 0.00, 5],
        ["Haysilo", "Low", 30.00, "Low", 88.45, 0.09, 0],
        ["Muzon", "Low", 30.00, "Low", 86.53, 0.00, 0],
        ["Niugan", "Low", 30.00, "Low", 90.95, 0.00, 0],
        ["Panghulo", "Very High", 30.35, "Low", 91.94, 38.39, 1],
        ["Potrero", "Very High", 30.00, "Moderate", 94.46, 12.64, 3],
        ["San Agustin", "Low", 32.58, "Low", 91.59, 0.00, 1],
        ["Santolan", "Low", 30.00, "Low", 89.72, 0.00, 0],
        ["Tanong", "Low", 30.00, "Low", 90.50, 0.00, 0],
        ["Tinajeros", "Very High", 38.73, "Moderate", 91.65, 31.54, 3],
        ["Tonsuya", "Very High", 30.00, "Low", 92.95, 32.62, 1],
        ["Tupatog", "Low", 30.00, "Low", 89.43, 0.00, 1]
    ]

    print()
    
    # Print table header
    print("=" * 95)
    print(f"{'BARANGAY':<18} {'LINEAR MODEL':<20} {'RANDOM FOREST':<20} {'CONFIDENCE'}")
    print(f"{'':<18} {'Risk':<10} {'Conf':<8} {'Risk':<10} {'Conf':<8} {'Difference'}")
    print("=" * 95)
    
    # Print data rows
    for row in data:
        barangay, linear_risk, linear_conf, rf_risk, rf_conf, linear_cases, rf_cases = row
        
        # Calculate confidence difference
        conf_diff = rf_conf - linear_conf
        
        # Color coding for confidence differences
        if conf_diff > 40:
            conf_indicator = "🟢🟢 RF +"
        elif conf_diff > 20:
            conf_indicator = "🟢 RF +"
        elif conf_diff > 10:
            conf_indicator = "🟡 RF +"
        elif conf_diff > 0:
            conf_indicator = "🟠 RF +"
        elif conf_diff < -40:
            conf_indicator = "🔴🔴 LINEAR +"
        elif conf_diff < -20:
            conf_indicator = "🔴 LINEAR +"
        elif conf_diff < -10:
            conf_indicator = "🟠 LINEAR +"
        else:
            conf_indicator = "⚪ TIE"
        
        print(f"{barangay:<18} {linear_risk:<10} {linear_conf:>6.1f}%  {rf_risk:<10} {rf_conf:>6.1f}%  {conf_diff:>+7.1f}% {conf_indicator}")
    
    print("=" * 95)
    
    # Calculate averages
    linear_confs = [row[2] for row in data]
    rf_confs = [row[4] for row in data]
    linear_cases_list = [row[5] for row in data]
    rf_cases_list = [row[6] for row in data]
    
    avg_linear_conf = sum(linear_confs) / len(linear_confs)
    avg_rf_conf = sum(rf_confs) / len(rf_confs)
    avg_linear_cases = sum(linear_cases_list) / len(linear_cases_list)
    avg_rf_cases = sum(rf_cases_list) / len(rf_cases_list)
    
    # Count risk level agreements
    risk_agreement = sum(1 for row in data if row[1] == row[3])
    total_comparisons = len(data)
    agreement_rate = (risk_agreement / total_comparisons) * 100
    
    # Confidence winners
    linear_wins = sum(1 for row in data if row[2] > row[4])
    rf_wins = sum(1 for row in data if row[4] > row[2])
    ties = sum(1 for row in data if row[2] == row[4])
    
    print(f"\n📈 AVERAGE CONFIDENCE:")
    print(f"   ┌{'─'*50}┐")
    print(f"   │ {'Linear Regression:':<25} {avg_linear_conf:>6.1f}% {'│':<10}")
    print(f"   │ {'Random Forest:':<25} {avg_rf_conf:>6.1f}% {'│':<10}")
    print(f"   │ {'Difference:':<25} {avg_rf_conf - avg_linear_conf:>+6.1f}% {'│':<10}")
    print(f"   └{'─'*50}┘")
    
    print(f"\n🔢 AVERAGE PREDICTED CASES:")
    print(f"   ┌{'─'*50}┐")
    print(f"   │ {'Linear Regression:':<25} {avg_linear_cases:>6.2f} cases {'│':<5}")
    print(f"   │ {'Random Forest:':<25} {avg_rf_cases:>6.2f} cases {'│':<5}")
    print(f"   │ {'Difference:':<25} {avg_rf_cases - avg_linear_cases:>+6.2f} cases {'│':<5}")
    print(f"   └{'─'*50}┘")
    
    print(f"\n🤝 RISK LEVEL AGREEMENT:")
    print(f"   ┌{'─'*50}┐")
    print(f"   │ {'Agreement Rate:':<20} {risk_agreement}/{total_comparisons} ({agreement_rate:.1f}%) {'│':<10}")
    print(f"   └{'─'*50}┘")
    
    print(f"\n🏆 CONFIDENCE COMPARISON:")
    print(f"   ┌{'─'*50}┐")
    print(f"   │ {'Linear Regression wins:':<25} {linear_wins:>2} barangays {'│':<8}")
    print(f"   │ {'Random Forest wins:':<25} {rf_wins:>2} barangays {'│':<8}")
    print(f"   │ {'Ties:':<25} {ties:>2} barangays {'│':<8}")
    print(f"   └{'─'*50}┘")
    
    # Confidence difference analysis
    conf_diffs = [row[4] - row[2] for row in data]
    avg_conf_diff = sum(conf_diffs) / len(conf_diffs)
    max_conf_diff = max(conf_diffs)
    min_conf_diff = min(conf_diffs)
    
    print(f"\n📊 CONFIDENCE DIFFERENCE ANALYSIS:")
    print(f"   ┌{'─'*50}┐")
    print(f"   │ {'Average Difference:':<20} {avg_conf_diff:>+7.1f}% {'│':<15}")
    print(f"   │ {'Maximum Difference:':<20} {max_conf_diff:>+7.1f}% {'│':<15}")
    print(f"   │ {'Minimum Difference:':<20} {min_conf_diff:>+7.1f}% {'│':<15}")
    print(f"   └{'─'*50}┘")
    
    # Key insights
    print(f"\n💡 KEY INSIGHTS:")
    print(f"   ┌{'─'*78}┐")
    print(f"   │ 🎯 Random Forest shows MUCH higher confidence (90.4% vs 31.2%)              │")
    print(f"   │ 📊 Average confidence difference: +59.2% in favor of Random Forest         │")
    print(f"   │ ⚠️  Risk levels disagree in nearly half of the barangays (47.6%)          │")
    print(f"   │ 🏆 Random Forest wins confidence comparison in ALL barangays              │")
    print(f"   │ 🔍 Maximum confidence gap: +64.5% (RF much more confident)                │")
    print(f"   └{'─'*78}┘")

# Run the function
if __name__ == "__main__":
    print_comparison_table()
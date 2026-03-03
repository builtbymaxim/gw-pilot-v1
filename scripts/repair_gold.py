import pandas as pd
import os

# Output-Datei
OUTPUT_FILE = 'gold60.csv'

# --- 1. THE VAGUE SET (Label = 0) ---
# Kriterien: Hedging words (aim, strive, intend), keine Zahlen, keine festen Jahre, viel "Corporate Fluff".
vague_sentences = [
    "We are committed to operating our business in a sustainable manner for the long term.",
    "Our ambition is to reduce our environmental footprint significantly over the coming years.",
    "We aim to explore opportunities to improve our energy efficiency across global operations.",
    "Management intends to assess climate-related risks as part of the broader risk framework.",
    "We believe that sustainability is a core component of our long-term strategic vision.",
    "We strive to foster a culture of inclusion and diversity throughout our workforce.",
    "The company is focused on transitioning towards a lower-carbon business model.",
    "We are currently evaluating the potential impact of climate change on our portfolio.",
    "Our goal is to support the transition to a net-zero economy through responsible investing.",
    "We expect to continue engaging with stakeholders on various ESG topics.",
    "We plan to enhance our disclosure regarding climate-related matters in future reports.",
    "We are making progress on our journey to become a more sustainable organization.",
    "We aspire to be a leader in corporate social responsibility within our industry.",
    "We are looking into ways to optimize our resource consumption and waste management.",
    "We anticipate that regulatory changes may impact our sustainability strategy.",
    "We seek to align our investment activities with broader environmental objectives.",
    "Our approach involves continuous monitoring of emerging ESG trends and risks.",
    "We are dedicated to maintaining high standards of corporate governance.",
    "We hope to achieve further improvements in our carbon intensity metrics over time.",
    "We are working towards integrating sustainability factors into our decision-making processes.",
    "We aim to minimize potential adverse impacts on the environment where feasible.",
    "We are considering the adoption of science-based targets in the near future.",
    "We endeavor to promote sustainable practices across our entire supply chain.",
    "We pledge to keep sustainability at the heart of our corporate values.",
    "We are taking steps to better understand our Scope 3 emissions profile.",
    "We intend to collaborate with industry peers to address common climate challenges.",
    "We are exploring the possibility of sourcing more renewable energy.",
    "Our strategy focuses on long-term value creation through sustainable growth.",
    "We aim to maintain open and transparent communication with our shareholders.",
    "We are committed to continuous improvement in all areas of environmental performance."
]

# --- 2. THE SPECIFIC SET (Label = 1) ---
# Kriterien: Harte Zahlen, Einheiten (tCO2e, %, €), konkrete Jahre (2025, 2030), vollständige Sätze.
specific_sentences = [
    "We will reduce absolute Scope 1 and 2 GHG emissions by 50% by 2030 from a 2019 base year.",
    "The company commits to sourcing 100% renewable electricity for its operations by 2025.",
    "We aim to achieve Net Zero emissions across our entire value chain by 2050.",
    "Our target is to reduce water intensity by 20% per unit of production by the end of 2025.",
    "We have invested €500 million in green bonds as of December 31, 2023.",
    "By 2030, we will reduce our Scope 3 emissions from purchased goods by 25%.",
    "We generated 450 GWh of renewable energy in 2023, an increase of 10% vs. 2022.",
    "Our Board comprises 40% female directors as of the 2024 Annual General Meeting.",
    "We pledge to eliminate single-use plastics from our packaging by 2026.",
    "Scope 1 emissions were 12,500 tCO2e in 2023, down from 14,000 tCO2e in 2022.",
    "We target a 30% reduction in fleet emissions by 2027 compared to 2020 levels.",
    "We will engage with 70% of our suppliers by spend to set science-based targets by 2028.",
    "The fund's carbon footprint is 120 tCO2e per $1 million invested as of Q4 2023.",
    "We aim to recycle 90% of our operational waste by the year 2025.",
    "Our executive remuneration policy links 15% of the annual bonus to ESG targets.",
    "We will plant 1 million trees in verified reforestation projects by 2030.",
    "We achieved a 5% reduction in energy consumption in 2023 compared to the previous year.",
    "Our goal is to have 50% of assets under management in Article 8 or 9 funds by 2025.",
    "We will audit 100% of our high-risk suppliers for human rights compliance by 2024.",
    "We target a reduction of methane intensity to 0.2% by 2025.",
    "By 2040, we aim to be fully carbon neutral across Scope 1, 2, and 3.",
    "We reduced our total waste to landfill by 2,000 metric tonnes in 2023.",
    "We will install 500 electric vehicle charging stations at our facilities by 2026.",
    "Our renewable energy capacity will increase to 5 GW by 2030.",
    "We target a 15% reduction in paper usage across all offices by 2025.",
    "We will invest $1 billion in climate transition technologies by 2030.",
    "Our portfolio temperature alignment is currently 2.5°C, targeting 1.5°C by 2050.",
    "We trained 3,000 employees on data privacy and security in 2023.",
    "We will reduce business travel emissions by 40% by 2025 vs. 2019.",
    "We target zero fatalities and a TRIR of less than 0.5 by 2025."
]

def main():
    print("--- Generiere sauberes Gold-Set ---")
    
    # Dataframes erstellen
    df_vague = pd.DataFrame({'text': vague_sentences, 'label_specific_target(0/1)': 0})
    df_specific = pd.DataFrame({'text': specific_sentences, 'label_specific_target(0/1)': 1})
    
    # Zusammenfügen
    df_gold = pd.concat([df_vague, df_specific], ignore_index=True)
    
    # IDs hinzufügen (wichtig für die spätere Identifikation)
    df_gold['item_id'] = ['GOLD_' + str(i).zfill(3) for i in range(len(df_gold))]
    
    # Spalten ordnen: Erst ID, dann Text, dann Label (nur zur Übersicht, Label wird beim Upload ja gelöscht)
    df_gold = df_gold[['item_id', 'text', 'label_specific_target(0/1)']]
    
    # Prüfungen
    print(f"Anzahl Vague (0): {len(df_vague)}")
    print(f"Anzahl Specific (1): {len(df_specific)}")
    print(f"Gesamtanzahl: {len(df_gold)}")
    
    # Speichern
    df_gold.to_csv(OUTPUT_FILE, index=False)
    print(f"Datei '{OUTPUT_FILE}' wurde erfolgreich erstellt/überschrieben.")

if __name__ == "__main__":
    main()
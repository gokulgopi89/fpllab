# FPLlab Metrics — Mathematical Quick Reference

---

## 5-METRIC SUMMARY

### 1️⃣ **xpts** (Expected Points) — The Main Score
```
What: Total projected points over next 5 gameweeks
Formula: Sum of (goals×multiplier + assists×3 + CS×points + bonus + defcon)
Range: 5–50 pts
Example: Haaland = 35 xpts over 5 GW
```

**How it's calculated:**
```
xpts = Σ(GW) [
  (goals90 × min_expected/90 × pos_mult × fixture_mult)  ← Goals value
  + (assists90 × min_expected/90 × 3 × fixture_mult)     ← Assist value
  + (P(CS) × cs_points)                                  ← Clean sheet value
  + (saves90 × fixture_mult / 3)                         ← Saves value
  + (bonus_expected)                                      ← Bonus points
  + (defcon_expected)                                     ← Defensive contributions
]
```

**Real example (Saka, 5 GW):**
```
GW1: 0.8 + 0.3 + 0.4 + 0.2 = 1.7 pts
GW2: 0.9 + 0.4 + 0.5 + 0.3 = 2.1 pts
GW3: 0.7 + 0.2 + 0.3 + 0.1 = 1.3 pts
GW4: 1.0 + 0.5 + 0.4 + 0.4 = 2.3 pts
GW5: 0.8 + 0.3 + 0.3 + 0.2 = 1.6 pts
xpts = 9.0 pts
```

---

### 2️⃣ **value** (Efficiency Metric) — ROI
```
What: Expected points per pound spent
Formula: xpts ÷ price (in £m)
Range: 1.0–5.0x
Example: Saka 28xpts ÷ £8.0m = 3.50x
```

**Value categories:**
```
< 1.5x   : Overpriced
1.5–2.0x : Okay
2.0–2.5x : Good
2.5–3.0x : Excellent
> 3.0x   : Exceptional
```

**Why it matters:**
```
Budget squad building:
- £100m total budget
- If avg value = 2.5x → 250 projected points
- If avg value = 2.0x → 200 projected points
- Every 0.1x improvement = 10 more points
```

**Example comparison:**
```
Option A: Haaland (£11.5m, 35 xpts)
→ value = 35/11.5 = 3.04x (very good)

Option B: Solanke (£7.4m, 18 xpts)
→ value = 18/7.4 = 2.43x (okay)

Option C: Saka (£8.0m, 28 xpts)
→ value = 28/8.0 = 3.50x (best value!)
```

---

### 3️⃣ **npxg90** (Shooting Ability) — Shot Quality
```
What: Expected goals per 90 minutes (non-penalty)
Formula: (Sum of xG from all shots) ÷ minutes × 90
Range: 0.0–0.6 per 90min
Example: Haaland = 0.57 npxg90
```

**What is xG (Expected Goals)?**
```
Each shot gets a probability score based on:
- Distance from goal (5y = 35%, 12y = 12%, 25y = 3%)
- Angle (straight = 20%, 30° = 8%, 45° = 4%)
- Defensive pressure (free = high%, defended = low%)
- Keeper position (off-guard = +10%, prepared = 0%)

Sum of all shots' xG = total expected goals
```

**Example shot:**
```
Shot from 12 yards, 15° angle, 1 defender:
Historical data: 12% of similar shots = goal
xG = 0.12
```

**Player comparison:**
```
Haaland: 45 shots (43 non-penalty)
         Total xG: 4.8
         Minutes: 720
         npxg90 = 4.8/720 × 90 = 0.60

Saka: 28 shots
      Total xG: 1.95
      Minutes: 1080
      npxg90 = 1.95/1080 × 90 = 0.16

Insight: Haaland takes 3.8x more shots
```

**Why it matters:**
```
- Identifies primary threat (shooter vs creator)
- Actual goals ~0.65–0.75 of xG (regression to mean)
- High npxg90 → Goals likely to come
- Low npxg90 + high assists → Creator, not scorer
```

---

### 4️⃣ **xa90** (Playmaking Ability) — Chance Creation
```
What: Expected assists per 90 minutes
Formula: (Sum of xA from key passes) ÷ minutes × 90
Range: 0.0–0.7 per 90min
Example: De Bruyne = 0.69 xa90 (elite)
```

**What is xA (Expected Assists)?**
```
A "key pass" immediately precedes a shot.
xA = xG of the resulting shot.

Example:
1. Player A passes to Player B
2. Player B shoots from 12 yards
3. That shot has 0.15 xG
4. Player A gets +0.15 xA credit
```

**Player example:**
```
De Bruyne (2023/24):
- 68 key passes
- Total xA: 9.2
- Minutes: 1200
- xa90 = 9.2/1200 × 90 = 0.69

Interpretation:
- Elite playmaker (top 0.1%)
- Generates high-quality chances constantly
- But depends on teammates finishing
```

**Position distribution:**
```
Creative midfielders: 0.30–0.70 xa90
Balanced midfielders: 0.15–0.30 xa90
Forwards: 0.05–0.25 xa90
Defenders: 0.00–0.10 xa90
Goalkeepers: 0.00 xa90
```

**Why it matters:**
```
- Separates true creators from lucky finishers
- Actual assists = xA × (teammate conversion rate)
- xA predictable year-to-year (repeats)
- Actual assists highly variable (luck-based)
```

---

### 5️⃣ **selected_by** (Market Indicator) — Ownership %
```
What: Percentage of FPL teams that own this player
Formula: (teams_owning ÷ total_teams) × 100
Range: 0.0–100%
Example: Haaland = 42% (highly owned)
```

**Ownership brackets:**
```
Elite (consensus):     > 40%  ← Everyone has them
High popularity:       20–40% ← Most players
Medium:                10–20% ← Good options
Low (underowned):       3–10% ← Value finds
Differential:          < 3%   ← Hidden gems
```

**Why ownership matters:**

1. **Captain strategy:**
```
If Haaland scores 48pts as captain (vs 24 if not):
- 42% of teams: +24pts gain
- 58% of teams: +0pts gain
- Difference between winning & losing

If Solanke scores 32pts as captain (1% owned):
- 99% miss these points
- Potential game-winner if you have him
```

2. **Price changes:**
```
FPL raises price when:
- More than +5,000 net transfers daily
- Each 5k threshold = £0.1m price rise

Example:
- Maddison rises 12% → 15% owned
- Price jumps £8.0m → £8.1m
- If bought at £8.0m, instant £0.1m gain
```

3. **Differential advantage:**
```
Your squad vs league average:

If your unique player (1% owned) scores +8pts:
- +8pts gain vs 99% of players
- Worth 100+ point swing in bracket rankings

If consensus player scores +8pts:
- Everyone gets +8pts
- No relative gain
```

**Formula for differential timing:**
```
Buy before ownership rises = price rises
Sell before ownership falls = price falls

Example:
Solanke: 1% owned, £7.0m
- Form improves (xpts 18 → 26)
- Ownership rises: 1% → 5%
- Price rises: £7.0m → £7.3m
- Gain: +£0.3m + ownership advantage
```

---

## HOW METRICS WORK TOGETHER

### **Complete Player Profile**

```
Player: Saka (Arsenal Midfielder)

xpts:        28.0    ← "Will score well" (yes)
value:       3.50x   ← "Is it efficient?" (excellent)
npxg90:      0.28    ← "Does he shoot?" (good)
xa90:        0.16    ← "Does he create?" (modest)
selected_by: 35%     ← "Is it consensus?" (yes)

Interpretation:
Saka is a high-quality attacking midfielder who:
- Projects to score 28 points (xpts)
- Gives 3.5 points per pound (value) — best on market
- Takes quality shots regularly (npxg90 = 0.28)
- Not primarily a playmaker (xa90 = 0.16)
- Widely owned (35%) — market agrees he's good
- Good pick both for safety AND value

Strategy:
- Safe pick (most teams have him)
- No massive differential upside
- BUT best value on market
- Use as trusted squad core
```

---

## COMPARISON: 3 Different Player Types

### **Player 1: Haaland (Scorer)**
```
xpts:        35.0   ✅ Elite
value:       3.04x  ✅ Excellent
npxg90:      0.57   ✅ Best shooter
xa90:        0.08   ❌ Limited creator
selected_by: 42%    ✅ Consensus

Profile: Elite goal scorer
Strategy: Essential squad member
Risk: Everyone has him (no differential)
```

### **Player 2: De Bruyne (Creator)**
```
xpts:        32.0   ✅ Elite
value:       2.88x  ✅ Very good
npxg90:      0.22   ⚠️ Moderate shooter
xa90:        0.69   ✅ Elite creator
selected_by: 38%    ✅ Consensus

Profile: Playmaker who creates gold-standard chances
Strategy: Essential midfielder
Risk: Few assists if teammates struggle
```

### **Player 3: Maddison (Hidden Gem)**
```
xpts:        24.0   ✅ Strong
value:       3.20x  ✅✅ BEST
npxg90:      0.25   ✅ Good
xa90:        0.32   ✅ Good
selected_by: 12%    ✅ UNDEROWNED

Profile: Balanced midfielder, severely underowned
Strategy: Buy before ownership rises
Upside: Price & points gain as market catches on
```

---

## MATHEMATICAL INSIGHTS

### **Regression to Mean (Why xpts Fluctuate)**

```
If Haaland has:
- xpts: 35 (expected)
- xG: 4.8 (expected goals)
- Actual goals: 2 (underperforming)

Next 5 GW prediction:
- Actual xpts likely: 36–38 (rebounds up)
- Explanation: Small sample variance
- 20 shots in 5 GW has luck variance

BUT if Haaland has:
- xpts: 35 (expected)
- xG: 4.8 (expected)
- Actual goals: 7 (overperforming)

Next 5 GW prediction:
- Actual xpts likely: 32–35 (regresses down)
- Explanation: 146% conversion rate unsustainable
- Expected to normalize toward 75–80%
```

### **Variance in Metrics**

```
Stable metrics (low variance):
- npxg90 (repeats year-to-year)
- xa90 (repeats year-to-year)
- value (if price/xpts accurate)

Variable metrics (high variance):
- xpts (depends on form, injuries, fixtures)
- selected_by (changes week-to-week)
- Actual goals (luck-based, ±20%)
```

### **The Optimal Portfolio**

```
Mathematics of value maximization:

Maximize: Σ(xpts_i) subject to:
- Σ(price_i) ≤ 100m
- 2 GK + 5 DEF + 5 MID + 3 FWD
- Max 3 from each club

Solution approach:
1. Rank by value (xpts / price)
2. Greedily select top value players
3. Ensure position constraints
4. Result: Squad with max points per pound
```

---

## QUICK CHEAT SHEET

| Metric | Formula | High | Low | Use |
|--------|---------|------|-----|-----|
| **xpts** | Sum of components | > 25 | < 15 | Overall quality |
| **value** | xpts ÷ price | > 3.0x | < 2.0x | Budget efficiency |
| **npxg90** | (xG) ÷ min × 90 | > 0.35 | < 0.15 | Scoring threat |
| **xa90** | (xA) ÷ min × 90 | > 0.30 | < 0.10 | Playmaking |
| **selected_by** | teams ÷ total | > 30% | < 5% | Consensus/differential |

---

## SUMMARY

**These 5 metrics answer:**

1. **xpts** → "Will this player score?"
2. **value** → "Is this good value for money?"
3. **npxg90** → "Does this player shoot/score?"
4. **xa90** → "Does this player create chances?"
5. **selected_by** → "Is this a safe pick or differential?"

Together = **360° view of player fantasy value**

All formulas based on real FPL scoring rules + statistical modeling (xG/xA from Understat).


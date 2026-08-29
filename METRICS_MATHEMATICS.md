# FPLlab v5 — Complete Mathematical Documentation

---

## METRIC 1: xpts (Expected Points)

### Definition
**Expected Points** = Projected fantasy points a player will score over the next 5 gameweeks, based on historical performance and fixture difficulty.

### Formula

```
xpts = Σ(GW=1 to 5) [ (rate_i × minutes_expected × fixture_multiplier) + bonus_expected + defcon_expected ]

Where:
  rate_i = Player's per-90-minute scoring rate (goals/assists/other)
  minutes_expected = Expected minutes played in that GW
  fixture_multiplier = Team's expected attacking/defensive strength in that fixture
  bonus_expected = Expected bonus points (if applicable)
  defcon_expected = Expected defensive contributions (if applicable)
```

### Component Breakdown

#### **1.1 Rate Calculation (per 90 minutes)**

```
goals90 = (goals_scored / total_minutes_played) × 90

Example:
- Player scored 5 goals in 1800 minutes last season
- goals90 = (5 / 1800) × 90 = 0.25 goals per 90 min
```

#### **1.2 Points from Goals**

```
points_from_goals = goals90 × expected_minutes × position_multiplier × fixture_multiplier

Position multipliers (FPL):
- Goalkeeper:  0 points per goal (can't score)
- Defender:    5 points per goal
- Midfielder:  5 points per goal
- Forward:     4 points per goal

Example (Midfielder):
- goals90 = 0.25
- expected_minutes = 90 (assuming full game)
- position_multiplier = 5
- fixture_multiplier = 1.0 (average difficulty)
- points = 0.25 × (90/90) × 5 × 1.0 = 1.25 points per game
```

#### **1.3 Points from Assists**

```
points_from_assists = assists90 × expected_minutes × 3 × fixture_multiplier

Where:
  assists90 = Assists per 90 minutes
  3 = Points per assist (all positions)
  fixture_multiplier = Team's expected offensive strength

Example:
- assists90 = 0.15
- expected_minutes = 90
- points = 0.15 × (90/90) × 3 × 1.0 = 0.45 points per game
```

#### **1.4 Points from Clean Sheets**

```
points_from_cs = P(CS) × cs_points × expected_minutes_ratio

Where:
  P(CS) = Probability of clean sheet (from Poisson distribution)
  cs_points = 4 (GK/DEF) or 1 (MID)
  expected_minutes_ratio = expected_minutes / 90

Poisson Model:
P(CS) = e^(-λ) 

Where λ = expected goals against (xGA)

Example (Defender vs team with xGA = 1.2):
- P(CS) = e^(-1.2) = 0.301 (30.1% chance)
- cs_points = 4
- points = 0.301 × 4 = 1.204 points per game
```

#### **1.5 Points from Saves**

```
points_from_saves = (saves90 × expected_minutes × fixture_multiplier) / 3

Where:
  saves90 = Saves per 90 minutes (GK only)
  1/3 = 0.33 points per save
  fixture_multiplier = Expected shot rate (xGF from opponent)

Example (Goalkeeper):
- saves90 = 4.5 saves per 90
- xGF_multiplier = 1.1 (team expected to face 1.1× average shots)
- points = (4.5 × (90/90) × 1.1) / 3 = 1.65 points per game
```

#### **1.6 Bonus Point Expected Value**

```
points_from_bonus = E[bonus] 

Where E[bonus] = Σ(bonus_scenarios) P(scenario) × points(scenario)

FPL Bonus Rules:
- 3 points: Top BPS scorer
- 2 points: 2nd place BPS
- 1 point: 3rd place BPS

Estimation (from historical BPS):
bonus_expected ≈ (historical_bonus_rate) × (fixture_multiplier)

Example:
- Player's historical bonus rate = 0.3 bonus points per game
- Fixture quality = 1.1
- expected_bonus = 0.3 × 1.1 = 0.33 points per game
```

#### **1.7 Defensive Contributions (DEF/GK)**

```
points_from_defcon = P(defcon) × 1 × expected_games

Where:
  P(defcon) = Probability of defensive contribution
  1 = 1 point per contribution
  expected_games = Expected games played

Calculated as:
P(defcon) = (historical_defcon_count / games_played)

Example (Defender):
- Historical: 2 defensive contributions in 20 games = 10% rate
- Expected games: 4.5
- points = 0.10 × 1 × 4.5 = 0.45 points
```

### **Total xpts Calculation**

```
xpts = Σ(GW=1 to 5) [ 
  points_from_goals +
  points_from_assists +
  points_from_cs +
  points_from_saves +
  points_from_bonus +
  points_from_defcon
]

Example (Star Midfielder over 5 GW):
GW1: 0.8 + 0.3 + 0.4 + 0 + 0.2 + 0 = 1.7 pts
GW2: 0.9 + 0.4 + 0.5 + 0 + 0.3 + 0 = 2.1 pts
GW3: 0.7 + 0.2 + 0.3 + 0 + 0.1 + 0 = 1.3 pts
GW4: 1.0 + 0.5 + 0.4 + 0 + 0.4 + 0 = 2.3 pts
GW5: 0.8 + 0.3 + 0.3 + 0 + 0.2 + 0 = 1.6 pts
─────────────────────────────────────
xpts = 9.0 points
```

### Why This Metric Matters
- **Purpose:** Direct FPL scoring prediction
- **Use:** "How many points will this player score?"
- **Audience:** Squad builders, transfer planners

### Limitations
- ❌ Assumes consistent form (no injury risk)
- ❌ Doesn't account for individual performance variance
- ❌ Bonus points are rough estimate
- ❌ Early season: limited historical data

---

## METRIC 2: value (Points per £1M)

### Definition
**Value** = Expected points generated per pound spent, showing investment efficiency.

### Formula

```
value = xpts / price

Where:
  xpts = Expected points (over 5 GW)
  price = Player cost in £millions

Example:
- Player A: £8m, 28 xpts → value = 28/8 = 3.5x
- Player B: £5m, 12 xpts → value = 12/5 = 2.4x
- Player C: £12m, 35 xpts → value = 35/12 = 2.92x

Ranking by value:
1. Player A (3.5x) ← Best value
2. Player C (2.92x)
3. Player B (2.4x)
```

### Understanding Value

**Value categories:**
```
< 1.5x  : Poor value (overpriced, low return)
1.5-2.0x: Below average
2.0-2.5x: Good value
2.5-3.0x: Excellent value
3.0-3.5x: Outstanding value
> 3.5x  : Exceptional value (rare)
```

### Value vs. Absolute Points Trade-off

```
High xpts, high price vs. Low xpts, low price:

Scenario 1: Premium player
- Haaland: £11.5m, 35 xpts
- Value = 35/11.5 = 3.04x
- Absolute points: 35 (best)
- Value: Good

Scenario 2: Budget player
- Solanke: £7.4m, 18 xpts
- Value = 18/7.4 = 2.43x
- Absolute points: 18 (lower)
- Value: Okay

Scenario 3: Elite value
- Saka: £8.0m, 28 xpts
- Value = 28/8.0 = 3.50x
- Absolute points: 28 (very good)
- Value: Excellent (combines both)
```

### Real FPL Application

**Squad-building constraint:**
```
Total squad cost ≤ £100m
Total squad points maximized

Using value metric:
- Rank all players by value/cost
- Pick top value players first
- Fill remaining budget with premium differentials
- Result: Balanced squad with good value

Example optimal squad (£100m):
- 2× GK at 2.0x value (£9m total) → 9 pts
- 5× DEF averaging 2.5x value (£35m) → 87.5 pts
- 5× MID averaging 3.0x value (£40m) → 120 pts
- 3× FWD averaging 2.8x value (£16m) → 44.8 pts
─────────────────────────────────────
Total: £100m, 261.3 pts
Average value: 2.61x
```

### Value Optimization Strategy

```
Step 1: Calculate value for all 600 players
Step 2: Sort by value (descending)
Step 3: Select top value players respecting:
  - Squad size: 15 players
  - Positions: 2 GK, 5 DEF, 5 MID, 3 FWD
  - Club limit: Max 3 from same club
  - Budget: ≤ £100m
Step 4: Result: Optimal value squad
```

### Why This Metric Matters
- **Purpose:** Identify efficiency, not just talent
- **Use:** "Which player gives best return for money?"
- **Audience:** Budget-conscious players, efficient squad builders

### Limitations
- ❌ Doesn't account for downside risk
- ❌ Assumes xpts are reliable
- ❌ Can overweight budget players
- ❌ Ignores captain potential (captain boost 2× value)

---

## METRIC 3: npxg90 (Non-Penalty Expected Goals per 90)

### Definition
**npxg90** = Expected goals per 90 minutes, excluding penalties. Measures a player's shooting ability and offensive output.

### Formula

```
npxg90 = (Σ(shots) xG_value) / (total_minutes) × 90

Where:
  xG_value = Expected goal value for each shot
  total_minutes = Minutes played
  90 = Standardization to per-90 basis
  Penalties excluded (hence "non-penalty")
```

### xG (Expected Goals) Model

#### **What is xG?**

Each shot is assigned a probability (0–1) of being a goal based on:
- Shot distance from goal
- Angle of shot
- Defensive pressure
- Goalkeeper position
- Historical goal rates for similar shots

#### **xG Calculation for Single Shot**

```
xG_shot = P(goal | shot characteristics)

Example shot analysis:
- Distance: 12 yards
- Angle: 15° from centerline (center = 0°)
- Defensive pressure: 1 defender within 3 yards
- Goalkeeper: Prepared (not caught off-guard)

Statistical model (from 1000s of historical data):
- Shots from 12 yards, 15° angle, 1 defender: 12% goal rate
- xG = 0.12

Interpretation:
- This shot has 12% chance of being a goal
- 100 similar shots → ~12 goals on average
```

#### **Advanced xG Features**

```
xG model adjusts for:
1. Distance (quadratic: closer = higher xG)
   - 5 yards: ~35% xG
   - 12 yards: ~12% xG
   - 25 yards: ~3% xG

2. Angle (sine curve: straight in front = higher)
   - 0° (straight on): ~20% xG
   - 30°: ~8% xG
   - 45°: ~4% xG

3. Pressure (binary or continuous)
   - No pressure: +5% xG
   - One defender: 0% xG
   - Multiple defenders: -10% xG

4. Keeper position
   - Off-guard: +10% xG
   - Prepared: 0% xG
   - Spread: +5% xG

5. Recent game state
   - After transition: +5% xG (more dangerous)
   - Set-piece: +15% xG
   - Open play: baseline
```

### npxg90 Calculation Example

```
Player: Mohamed Salah (2024/25)
Season data (to GW10):
- 45 shots taken
- 2 penalties (excluded)
- 43 open-play shots
- Total xG from 43 shots: 4.8 xG
- Total minutes: 720 (8 full games)

npxg90 = (4.8 / 720) × 90
        = 0.6 npxg90

Interpretation:
- Salah averages 0.6 expected goals per 90 minutes
- If he played 3 full 90-minute games: ~1.8 expected goals
- Actual goals: 2 (better than expected, lucky/clinical)
```

### Comparing Players by npxg90

```
Top scorers by npxg90 (2024/25):
1. Haaland: 0.57 npxg90  ← Elite finisher, high volume
2. Saka: 0.28 npxg90     ← Good shooter, fewer attempts
3. Odegaard: 0.18 npxg90 ← Creator, not primary scorer
4. Mount: 0.15 npxg90    ← Limited chances

Insight: Haaland takes 3x more shots than Saka
- More volume opportunities
- More predictable goal output
```

### Seasonality & Clustering

```
npxg90 tiers by position:

Forwards (xG creators):
- Top tier: 0.40–0.60 (Haaland, Kane)
- Middle: 0.25–0.40 (good strikers)
- Lower: 0.10–0.25 (backup forwards)

Midfielders:
- Top: 0.25–0.40 (attacking mids)
- Middle: 0.15–0.25 (balanced mids)
- Lower: 0.05–0.15 (defensive mids)

Defenders:
- Top: 0.05–0.15 (aerial threat, set-pieces)
- Lower: 0.00–0.05 (pure defenders)

Goalkeepers:
- Always: 0.00 (can't score)
```

### Why This Metric Matters
- **Purpose:** Measure shooting quality & efficiency
- **Use:** "How dangerous is this player offensively?"
- **Audience:** Forward/MID analysts, xG enthusiasts

### Limitations
- ❌ Only measures shooting (not assists, deflections)
- ❌ Actual goals vary by luck (sample variance)
- ❌ Doesn't account for set-pieces separately
- ❌ xG model varies by source (Understat, Statsbomb, Opta)

### Real xG vs. Actual Goals

```
Why shots don't convert perfectly:

Player A: 4.2 xG, 3 goals
- Underperforming by 1.2 goals
- Less clinical, missed chances
- Next 5 GW: May improve (regression to mean)

Player B: 2.8 xG, 5 goals
- Overperforming by 2.2 goals
- Very clinical, excellent conversion
- Next 5 GW: May regress (unsustainable)

FPL Strategy:
- Underperformers: Might be due "goals soon"
- Overperformers: Caution, may not sustain
```

---

## METRIC 4: xa90 (Expected Assists per 90)

### Definition
**xa90** = Expected assists per 90 minutes. Measures a player's playmaking ability and chance creation.

### Formula

```
xa90 = (Σ(key passes) xG_of_resulting_shot) / (total_minutes) × 90

Where:
  key_pass = Pass that immediately leads to a shot
  xG_of_resulting_shot = xG value of resulting shot
  total_minutes = Minutes played
  90 = Standardization
```

### xA (Expected Assists) Calculation

#### **What is a Key Pass?**

```
Definition: A pass that immediately precedes a shot attempt.

Example:
1. Player A passes to Player B
2. Player B shoots within 1–2 touches
3. Player A gets 1 key pass credit
4. xA = xG of Player B's shot

If Player B's shot = 0.15 xG:
   Player A gets +0.15 xA credit
```

#### **xA Model**

```
xA = Σ(passes) P(pass leads to shot) × P(shot scores)

Breaking it down:

Step 1: Identify key passes
- Straight line to goal (not lateral)?
- Direct to teammate?
- Within shooting distance?
- Score: Yes/No → key pass or not

Step 2: Weight by shot quality
- Shot from 5 yards: xA ≈ 0.08
- Shot from 12 yards: xA ≈ 0.05
- Shot from 20 yards: xA ≈ 0.02
- Blocked shot: xA ≈ 0.01
- Weak shot: xA ≈ 0.005

Step 3: Normalize to per-90
xa90 = (total_xA / minutes) × 90
```

### xa90 Examples

```
Example 1: Creative Midfielder (De Bruyne)
Season data:
- 68 key passes
- Total xA from key passes: 9.2
- Minutes: 1200 (13.3 games)

xa90 = (9.2 / 1200) × 90
     = 0.69 xa90

Interpretation:
- Creates ~0.69 expected assists per 90 min
- If plays 2 games: ~1.4 expected assists
- Extremely creative (elite level)
```

```
Example 2: Winger (Saka)
Season data:
- 45 key passes
- Total xA: 5.8
- Minutes: 1080

xa90 = (5.8 / 1080) × 90
     = 0.48 xa90

Interpretation:
- Very good creatively
- Not as extreme as elite playmaker
- Mix of goals + assists likely
```

```
Example 3: Defender (Van Dijk)
Season data:
- 8 key passes (mostly set-pieces)
- Total xA: 0.4
- Minutes: 1200

xa90 = (0.4 / 1200) × 90
     = 0.03 xa90

Interpretation:
- Minimal playmaking (pure defender)
- Occasional set-piece assists
- Scoring ability far more likely
```

### xa90 Distribution by Position

```
Playmakers (Creative Midfielders/Wingers):
- Top tier: 0.30–0.70 (De Bruyne, Madision, Saka)
- High: 0.20–0.30 (good creators)
- Medium: 0.10–0.20 (balanced mids)

Forwards:
- Top: 0.15–0.30 (playmaking strikers, like Kane)
- Middle: 0.05–0.15 (goal-focused forwards)
- Lower: 0.00–0.05 (pure finishers)

Defenders:
- High: 0.05–0.15 (ball-playing defenders, full-backs)
- Medium: 0.02–0.05 (set-piece creators)
- Lower: 0.00–0.02 (pure defenders)

Goalkeepers:
- Always: 0.00 (can't assist)
```

### xA vs. Actual Assists

```
Why assists don't match xA:

Player A: 5.8 xA, 3 assists
- Underperforming by 2.8
- Teammates missing chances
- Luck factor: 51% (3/5.8) vs. expected ~60%
- Next 5 GW: May see assist spike (regression)

Player B: 3.2 xA, 5 assists
- Overperforming by 1.8
- Teammates very clinical
- Luck factor: 156% vs. expected 100%
- Next 5 GW: May regress
```

### Why This Metric Matters
- **Purpose:** Measure chance creation independent of teammates
- **Use:** "How creative/playmaking is this player?"
- **Audience:** MID/WID analysts, creative squad builders

### Limitations
- ❌ Depends on teammate finishing (not player's fault)
- ❌ Actual assists often lower (teammates miss)
- ❌ Doesn't capture "hockey assist" (setup to the assister)
- ❌ Set-pieces vary year to year
- ❌ Sample variance: small number of actual assists

---

## METRIC 5: selected_by (Ownership %)

### Definition
**selected_by** = Percentage of FPL teams that own this player. Measures popularity and market confidence.

### Formula

```
selected_by = (teams_owning_player / total_teams) × 100

Where:
  teams_owning_player = How many teams have this player
  total_teams = ~8–10 million FPL teams
  Result = Percentage (0–100%)

Example:
- 4.2 million teams own Haaland
- 10 million total teams
- selected_by = (4.2 / 10) × 100 = 42%
```

### Ownership Categories

```
Elite (Consensus):     > 40%  (Haaland, Saka, key premium)
High popularity:       20–40% (popular premium/mid-price)
Medium:                10–20% (good options, not must-have)
Low:                    3–10% (undervalued or risky)
Differential:          < 3%   (hidden gems or risky moves)
```

### Why Ownership Matters

#### **Captaincy Strategy**

```
Haaland: 42% selected
- If Haaland captain gets 48 pts (vs. 24 if VC)
- 42% of teams get +24 pts
- 58% of teams get +0 pts
- Difference = huge

Solanke (differential): 1% selected
- If you captain him and get 32 pts
- Only 1% have him as VC backup
- 99% of teams miss these points
- Huge differential advantage

Strategy:
- High ownership on differentials = bad (everyone has it)
- Low ownership captain = potential game-winner
- Consensus captain = safe (won't hurt relative standing)
```

#### **Transfer Timing**

```
Price change mechanism:
- When player bought by > 5% more teams: price rises
- When player sold by > 5% more teams: price falls

Example:
- Salah: 35% → rises to high price
- Then Salah injury: 35% → 20% (crashes)
- Price falls from £9.0m to £8.5m

FPL opportunity:
- Buy before ownership spike (price rise)
- Sell before ownership collapse (price fall)
```

### Ownership vs. Expected Points Trade-off

```
High ownership, high xpts (consensus pick):
- Example: Haaland at £11.5m, 35 xpts, 42% owned
- Safe: Everyone has him
- Risk: No differential upside
- ROI: Normal

High xpts, low ownership (differential):
- Example: Solanke at £8.0m, 26 xpts, 1% owned
- Risk: Unknown, "could fail"
- Upside: If correct, massive advantage
- ROI: 10–50x if right, 0x if wrong

Low xpts, high ownership (trap):
- Example: Injured player still highly owned
- Risk: Everyone has him as negative
- Bad: Everyone loses together

Smart strategy:
- Mix of: 70% consensus + 30% differential
```

### Ownership Trends Over Season

```
Gameweek-by-gameweek changes:

GW1: Mixed (new season, uncertainty)
- New signings low (1–2%)
- Last year's stars high (30–40%)

GW2–5: Stabilization
- Good form players rise
- Bad form players fall
- Trending: +5–10% per GW

GW10+: Fixture cycles
- Easy run ahead: +5–20% rise
- Hard run ahead: -5–10% fall

Mid-season: Differential opportunities
- Players with good xpts but low ownership
- Example: Midfielder with 0.4 xa90 but only 8% owned

End of season: Consolidation
- Top options converge to high ownership (25–50%)
- Differentials less effective
```

### Relationship with Price Change

```
Price update mechanism (FPL):
- Net transfers = In transfers - Out transfers
- If net > +5k transfers per day: Price +£0.1m
- If net < -5k transfers per day: Price -£0.1m

In dollars (metaphorical ownership):
- Haaland: 42% ownership, £11.5m
  If 100k new teams buy: +0.1m rise to £11.6m
  
- Solanke: 1% ownership, £8.0m
  If 5k new teams buy: No change yet
  If 50k new teams buy: +0.1m rise to £8.1m

Insight:
- Cheap underowned players can spike in price
- Expensive overowned players stable or fall

Trading edge:
- Buy underowned, good xpts players before ownership rise
- Sell overowned declining players before price fall
```

### Why This Metric Matters
- **Purpose:** Assess market inefficiency & differentiation
- **Use:** "Is this player consensus or differential?"
- **Audience:** Strategy players, captain deciders, transfer planners

### Limitations
- ❌ Not predictive (lagging indicator)
- ❌ Changes daily (real-time swings)
- ❌ Doesn't explain WHY high/low ownership
- ❌ Early season: less meaningful (few gameweeks of data)
- ❌ Can create "false consensus" (everyone copying)

---

## METRIC CORRELATIONS

### Cross-metric relationships

```
Correlation matrix (hypothetical):

                xpts   value  npxg90  xa90   ownership
xpts            1.00   0.70   0.75    0.65   0.55
value           0.70   1.00   0.60    0.50   0.30
npxg90          0.75   0.60   1.00    0.40   0.50
xa90            0.65   0.50   0.40    1.00   0.45
ownership       0.55   0.30   0.50    0.45   1.00

Insights:
- xpts & npxg90 highly correlated (0.75): shooting power matters for points
- xpts & value moderate (0.70): price doesn't always reflect xpts
- value & ownership low (0.30): cheap players not always owned
- npxg90 & xa90 low (0.40): can't be both shooter and creator
```

### Finding Undervalued Players

```
Smart scouting algorithm:

Rank all players by:
(xpts + value + npxg90 + xa90) / ownership

This finds:
- High expected points (xpts)
- Efficient cost (value)
- Good shot output (npxg90)
- OR good creation (xa90)
- WITHOUT high consensus (low ownership)

Example result:
- Solanke: 26 xpts, 3.25 value, 0.35 npxg90, 0.12 xa90, 1% owned
- Score = (26 + 3.25 + 0.35 + 0.12) / 0.01 = 2,972
- Ranked #5 in smartness
- Haaland: 35 xpts, 3.04 value, 0.57 npxg90, 0.08 xa90, 42% owned
- Score = (35 + 3.04 + 0.57 + 0.08) / 0.42 = 100
- Ranked #50 (consensual, no edge)
```

---

## SUMMARY TABLE: All Metrics

| Metric | Formula | Interpretation | Range | Use Case |
|--------|---------|-----------------|-------|----------|
| **xpts** | ∑(goals + assists + CS + bonus) | Total expected points | 5–50 | "Who scores most?" |
| **value** | xpts / price | Points per £m | 1–5x | "Best bang for buck?" |
| **npxg90** | (∑xG / minutes) × 90 | Shots per 90min | 0–0.6 | "Who shoots best?" |
| **xa90** | (∑xA / minutes) × 90 | Creates per 90min | 0–0.7 | "Who creates best?" |
| **selected_by** | (teams_owning / total_teams) × 100 | Ownership % | 0–100% | "Is this consensus?" |

---

## PRACTICAL EXAMPLE: Complete Analysis

### Scouting Report for 3 Players

#### **Player 1: Harry Kane (Tottenham)**
```
xpts:         32.0 pts      (Elite)
value:        2.65x         (Good)
npxg90:       0.38          (Strong shooter)
xa90:         0.22          (Playmaker element)
selected_by:  38%           (High consensus)

Analysis:
- Strong all-around player
- Mix of goals + assists
- Expensive (£11.8m) but justified
- Most teams own him (safe)
- Low upside (already priced in)
- Use as captain in good run
```

#### **Player 2: Antony (Manchester United)**
```
xpts:         16.0 pts      (Moderate)
value:        2.35x         (Decent)
npxg90:       0.18          (Weak shooter)
xa90:         0.14          (Limited creator)
selected_by:  8%            (Underowned)

Analysis:
- Underperforming player
- xpts disappointing for midfield
- Low value (not cheap enough)
- Weak both ways (shooting + creation)
- Massively underowned (but for reason)
- Avoid unless form improves
```

#### **Player 3: Maddison (Leicester)**
```
xpts:         24.0 pts      (Very Good)
value:        3.20x         (Excellent)
npxg90:       0.25          (Good shooter)
xa90:         0.32          (Elite creator)
selected_by:  12%           (Underowned)

Analysis:
- Hidden gem (strong xpts, low price)
- Balanced: both creates + shoots
- Exceptional value (best on market)
- Severely underowned (market inefficiency!)
- Strong differential pick
- Buy before ownership rises
- Price will go up as ownership rises
```

### Investment Strategy Based on Metrics

```
Budget: £100m to spend

Strategy A: Consensus (Safe)
- Buy top owned players
- Example: Haaland (42%), Saka (35%), Van Dijk (28%)
- xpts: ~80, price: £30m
- Pro: Won't lose relative standing
- Con: No upside vs. competition

Strategy B: Differential (Risky)
- Buy underowned good value players
- Example: Maddison (12%), Solanke (1%), Mazraoui (5%)
- xpts: ~75, price: £25m
- Pro: Gain 5–10 points on others
- Con: If wrong, lose 5–10 points

Strategy C: Balanced (Recommended)
- Mix: 70% consensus + 30% differential
- 10 consensus (1–2% value gain)
- 5 differential (3–5% value gain)
- Expected overall advantage: +1–2%
- Risk: Moderate
```

---

## CONCLUSION: Why These 5 Metrics?

1. **xpts** — Answers: "Will this player score points?"
2. **value** — Answers: "Is this player efficient?"
3. **npxg90** — Answers: "Does this player shoot?"
4. **xa90** — Answers: "Does this player create?"
5. **selected_by** — Answers: "Am I taking a differential?"

Together, they provide **360° view** of any player's Fantasy value.


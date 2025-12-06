You are playing Doom II on DOS. Your goal is to complete the level and reach the first checkpoint without dying. You are playing the regular difficulty of "Hurt me plenty".

## 1. Primary Goals and Prioritization (STRICT ORDER)
Your actions MUST be guided by the following strict priority order. An action from a lower priority can only be taken if all higher priorities are satisfied.
1. **SURVIVE (Health > 50):** If Health < 50, immediately retreat (S,S,S) or strafe (A or D) AND seek a Health Pack/Armor.
2. **ENGAGE & ELIMINATE HOSTILE THREATS (STOP-FIGHT-PROCEED):** The moment an enemy is sighted, **HALT ALL EXPLORATION (STOP)**. Do not proceed until the threat is eliminated.
3. **EXPLORE & PROGRESS:** Find and open doors to move toward the next checkpoint.
4. **RESOURCE MANAGEMENT:** Track and collect Ammo and Health Packs.

## 2. Combat Protocol (Precision and Aggression)
**ABSOLUTE RULE: DO NOT WALK INTO OR PAST AN ENEMY.**
* **The Kill-Gate:** If you see an enemy, your next moves must be centered around killing it. Moving past it means certain death from the back.
* **Targeting Loop for Lag Compensation:** Do NOT fire until the enemy is **perfectly centered** and stable. After firing, immediately use ArrowLeft or ArrowRight to make a micro-adjustment and check if the enemy is still centered. This is a rapid-fire **Aim -> Fire -> Re-Aim** loop.
* **Movement while Shooting:** You are a fast target. **Never stand still** while shooting. Use `A` or `D` repeatedly to strafe side-to-side while maintaining your forward aim and firing (`A,Control,D,Control,A,Control...`).
* **Immediate Rear Threat Response:** If your screen flashes red AND you do not see an enemy in front: You have **3 ACTS** to kill the rear threat.
    1.  First Act: **ArrowLeft** (repeated 14 times for 90-degrees).
    2.  Second Act: **ArrowLeft** (repeated 14 times for 90-degrees, total 180-degrees).
    3.  Third Act: **Control** (Fire immediately at the now-visible threat). Do not pause.

## 3. Navigation and Action Economy
* **Action Conservation (The Click Economy):** Do not spam keys. Every key press costs valuable time. You must use the **minimum number of key repetitions** to achieve the desired effect.
    * **90-Degree Turn:** Use `ArrowLeft` or `ArrowRight` **14 times** separated by commas. Do not overshoot.
    * **Pick-Up:** When aligning to pick up an item (Health/Ammo), use `ArrowLeft/Right` for fine-tuning. Only press `W` the minimum number of times to collect it (e.g., `W,W,W` max). Do not waste time circling the item.
* **Door Identification (Visual Checkpoint):**
    1.  Are there two pillars with a blue triangle design?
    2.  Is there a clear rectangular structure between them with some writing (e.g., UAC)?
    3.  If YES, move forward and align to open. If NO, continue exploring the corridor. **Do not mistake the pillars themselves for the door.**

## 4. Forced Chain-of-Thought (CoT) Reasoning
BEFORE providing the action, you **MUST** output a Thought in the following structured format. This ensures fast, logical, and accountable decision-making.

**Thought:**
1. **Health/Ammo Status:** [e.g., Health 85%, Ammo 28. Status: READY TO ENGAGE]
2. **Action Priority:** [e.g., ENGAGE THREAT / EXPLORE (Door Check) / SURVIVE (Retreat)]
3. **Reasoning:** [e.g., Enemy centered, must fire while strafing D. OR T-junction seen, checking for door before turning. OR Rear threat detected, executing 180-degree turn immediately.]

## 5. Controls Summary (Use Sparingly)
- `ArrowLeft`, `ArrowRight`: Look/Adjust Aim
- `W`, `A`, `S`, `D`: Move forward, left, back, right
- `Control`: Fire weapon
- `Space`: Open door / Interact



<!-- reflections on this prompt: 

1. performance was worse compared to previous prompt 1.

2. agent kept shooting incorrectly, wasted ammo, also actions seemed incorrect.

3. for the pause on the screen it kept pressin escape when this has never happened before! since videogamebench lite always pauses after certain frames it shouldve just ignored like it ignored till now. but right now it kept getting stuck in the loop of fixing the pause issue which is not our goal. 
 -->

 Issue,Technique Refinement,Implementation Focus
1. Missing Enemies/Walking Past,"Immediate, Aggressive Engagement Constraint","STOP-FIGHT-PROCEED: Force the agent to halt exploration the moment an enemy is sighted, and make Elimination an absolute gate to further movement."
2. Wasted Time/Rotation Miscalculation,Rotation/Movement Economy & Feedback Loop,"Fine-Grained Feedback: Double-down on minimizing non-essential key repeats. Force the agent to only use the exact number of clicks necessary for alignment, and acknowledge the lag/slippage in its movement."
3. Missing Doors,Visual Feature Reinforcement & Checkpoint,"Hierarchical Vision Check: Make the door identification process a highly prioritized, sequential visual check that the agent must explicitly confirm before continuing."
You are playing Doom II on DOS. Your goal is to complete the level and reach the first checkpoint without dying. You are playing the regular difficulty of "Hurt me plenty".

## 1. Primary Goals and Prioritization (DO NOT FORGET)
Your actions MUST be guided by the following strict priority order:
1. **SURVIVE (Health > 50):** If Health < 50, immediately seek a Health Pack or retreat and strafe to avoid damage.
2. **ENGAGE & ELIMINATE:** Kill any hostile enemy (red/green figures) in your line of sight.
3. **EXPLORE & PROGRESS:** Find the path forward, open doors, and move toward the next checkpoint.
4. **RESOURCE MANAGEMENT:** Track and collect Ammo and Health Packs (including armor).

## 2. Combat Protocol (Precision and Speed)
The game is real-time. You must act decisively to avoid taking damage.
* **Targeting Loop:** Do NOT shoot until the enemy is **centered** on your screen. After every shot, immediately re-evaluate the target's position. If the enemy has moved, **RE-CENTER and then shoot**. Do not waste ammo.
* **Movement while Shooting:** If you are being shot at (screen flashes red) OR when engaging an enemy, **NEVER STAND STILL.** Use W/A/S/D or Shift+Movement to constantly strafe or move while aiming and firing. This is crucial for survival.
* **Enemy Lag Compensation:** Assume the enemy will move between the observation and your action. Center your aim, shoot, and immediately **adjust your aim for the next shot**. If you miss, you were off target—RE-ADJUST.
* **Rear Threat:** If your screen flashes red and no enemy is in front, **IMMEDIATELY** turn 180 degrees (ArrowLeft or ArrowRight repeated) and engage the threat.

## 3. Navigation and Exploration (Efficiency and Memory)
* **Path Memory:** When taking a turn, explicitly note the direction taken (e.g., 'Turned Right from Junction A'). This prevents you from **overturning** (going past a 90-degree corner) or making **redundant movements** (going back the way you came, unless retreating).
* **Corridor Travel:** Follow corridors. Only turn at junctions or to engage enemies. Use the minimum number of key presses to achieve a 90-degree turn to avoid over-steering.
* **Door Identification:** A door is usually located **between two pillars** with a blue triangle design and will have writing (e.g., UAC).
    * To open: Align the door to the screen center, walk up until you are pressed against it, and press **Space**. You cannot open it from afar.
    * **Post-Door Check:** If you open a door and the room is empty, **immediately exit** and continue exploring the main path.

## 4. Forced Chain-of-Thought (CoT) Reasoning
BEFORE providing the action, you **MUST** output a Thought in the following structured format. This is your internal reasoning process.

**Thought:**
1. **State Check (Health/Ammo):** [e.g., Health 85%, Ammo 28. Status: OK.]
2. **Current Priority:** [e.g., SURVIVE / ENGAGE / EXPLORE]
3. **Observation & Analysis:** [e.g., Enemy sighted on the right. Currently not centered. OR At a T-junction, previously came from the left. OR Screen flashed red, turning to check rear.]
4. **Action Rationale:** [e.g., Must strafe left while aiming to center the enemy, then fire. OR Turning right 90 degrees to follow the corridor. OR Moving forward to collect the ammo clip.]

## 5. Controls Summary (Use Finer Control for Combat)
- `ArrowLeft`, `ArrowRight`: Look/Adjust Aim (Use for fine-tuning)
- `W`, `A`, `S`, `D`: Move forward, left, back, right (Use W to explore, A/D to strafe in combat)
- `Shift + W`, `A`, `S`, `D`: Run
- `Control`: Fire weapon (Use only when centered)
- `Space`: Open door / Interact

**90-Degree Turn:** Repeat `ArrowLeft` or `ArrowRight` **14 times** separated by commas.
**Forward Movement:** Repeat `W` multiple times separated by commas, e.g., `W,W,W,W,W`.






<!-- 

1. it missed enemies alot, and sometimes walked through them, and when it did walk through them, the enemies shot agent from the back but agent took time to rotate and got his health super low.. maybe kill and proceed would be better than walking into enemy.

2. also wasted a lot of time in picking the healthpack, the agent doesnt understand how many times clicking single button gives how much rotation, and based on view it gets it miscalculated its steps,

3. agent also missed the door.

 -->






Technique,Description,Impact on Performance
Chain-of-Thought (CoT) Structuring,"Providing a mandatory, structured format for the agent's ""Thought"" process before the action. This forces explicit, sequential reasoning.","Reduces lag and improves action timing. Forces the agent to rapidly prioritize and decide, minimizing the time between observation and action."
Negative Constraints/Guardrails,"Explicitly stating common failure modes (overturning, redundant movement, shooting without centering) and demanding they be avoided.",Enhances navigation and combat accuracy. Directly addresses your issues with overturning and wasted shots.
Real-Time Combat Heuristics,"Introducing high-priority rules for combat, such as strafing/moving while shooting and a rapid, iterative aiming loop that demands re-evaluation after every action.",Improves survivability and combat effectiveness. Addresses the issue of the enemy moving after the frame is captured.
Memory Augmentation & State Tracking,"Creating structured prompts to force the agent to update and use its internal map/state (health, ammo, last turn).",Boosts exploration and pathfinding. Helps the agent remember where it has been and prevents getting stuck or going in circles.
Goal Decomposition & Prioritization,Breaking down the main goal (complete the game) into a prioritized list of sub-goals (Survive > Kill > Explore > Get Items).,Ensures focus on survival and core objectives. Prevents the agent from exploring when it should be fighting.
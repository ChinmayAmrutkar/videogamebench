You are playing Doom II on DOS. Your goal is to complete the level and reach the first checkpoint without dying. You are playing the regular difficulty of "Hurt me plenty".

## 1. Primary Goals and Prioritization (DO NOT FORGET)
Your actions MUST be guided by the following strict priority order:
1. **SURVIVE (Health > 50):** If Health < 50, immediately seek a Health Pack or retreat and strafe to avoid damage.
2. **ENGAGE & ELIMINATE HOSTILE THREATS (KILL-GATE):** Kill any hostile enemy (red/green figures) in your line of sight. **DO NOT walk past or through an active enemy. Elimination must precede exploration.**
3. **EXPLORE & PROGRESS:** Find the path forward, open doors, and move toward the next checkpoint.
4. **RESOURCE MANAGEMENT:** Track and collect Ammo and Health Packs (including armor).

## 2. Combat Protocol (Precision and Speed)
The game is real-time. You must act decisively to avoid taking damage.
* **Targeting Loop:** Do NOT shoot until the enemy is **centered** on your screen. After every shot, immediately re-evaluate the target's position. If the enemy has moved, **RE-CENTER and then shoot**. Do not waste ammo.
* **Movement while Shooting:** If you are being shot at (screen flashes red) OR when engaging an enemy, **NEVER STAND STILL.** Use W/A/S/D or Shift+Movement to constantly strafe or move while aiming and firing. This is crucial for survival.
* **Enemy Lag Compensation:** Assume the enemy will move between the observation and your action. Center your aim, shoot, and immediately **adjust your aim for the next shot**. If you miss, you were off target—RE-ADJUST.
* **Rear Threat:** If your screen flashes red and no enemy is in front, **IMMEDIATELY** turn 180 degrees (ArrowLeft or ArrowRight repeated) and engage the threat.

## 3. Navigation and Exploration (Unblock Mandate)
* **UNBLOCK MANDATE (CRITICAL):** If your current action has resulted in no visible change for three consecutive frames (e.g., stuck on a wall, circling the starting room), the next action MUST be a turn (`ArrowLeft` or `ArrowRight`) followed by forward movement (`W,W,W,W,W`) to actively seek the corridor exit. **Do not get stuck roaming the start area.**
* **Path Memory:** When taking a turn, explicitly note the direction taken (e.g., 'Turned Right from Junction A'). Use the minimum number of key presses (Arrow keys repeated 14 times for 90 degrees) to turn.
* **Door Identification:** A door is usually located **between two pillars** with a blue triangle design and will have writing (e.g., UAC).
    * To open: Align the door to the screen center, walk up until you are pressed against it, and press **Space**.
* **Resource Collection Efficiency:** When collecting a health pack or ammo, only use the minimum number of forward key presses (e.g., `W` repeated 1-3 times) to acquire the item. **Do not spend time circling or over-adjusting.**

## 4. Forced Chain-of-Thought (CoT) Reasoning
BEFORE providing the action, you **MUST** output a Thought in the following structured format. This is your internal reasoning process.

**CRITICAL GUARDRAIL:** The game may pause frequently due to the benchmark system. **IGNORE these pauses and do not press the ESCAPE key or any other interaction key** to try and fix them. Focus only on the game state when the screen is active.

**Thought:**
1. **State Check (Health/Ammo):** [e.g., Health 85%, Ammo 28. Status: OK.]
2. **Current Priority:** [e.g., SURVIVE / ENGAGE / EXPLORE (MUST UNBLOCK)]
3. **Observation & Analysis:** [e.g., Enemy sighted on the right, must eliminate before proceeding. OR Stuck for 3 frames, initiating UNBLOCK MANDATE: turn left and move forward. OR Found door, aligning to press Space.]
4. **Action Rationale:** [e.g., Must strafe left while aiming to center the enemy, then fire. OR Turning right 90 degrees to follow the corridor. OR Moving forward to collect the ammo clip.]

## 5. Controls Summary (Use Finer Control for Combat)
- `ArrowLeft`, `ArrowRight`: Look/Adjust Aim (Use for fine-tuning)
- `W`, `A`, `S`, `D`: Move forward, left, back, right (Use W to explore, A/D to strafe in combat)
- `Shift + W`, `A`, `S`, `D`: Run
- `Control`: Fire weapon
- `Space`: Open door / Interact

**90-Degree Turn:** Repeat `ArrowLeft` or `ArrowRight` **14 times** separated by commas.
**Forward Movement:** Repeat `W` multiple times separated by commas, e.g., `W,W,W,W,W`.



<!-- this is the furthest the agent has ever reached but unfortunately dies before reaching a checkpoint,


it was successfully able to open a door! very first time!


congrats. but unfortunately after opening it it didnt enter through the door, which the agent was supposed to do and went back and pverrotated and returned back to starting point! it was painful to watch after simulation of 1 hour!


and then agent was just stuck in the starting point area itself!!!

 -->
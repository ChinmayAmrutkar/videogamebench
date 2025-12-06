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

## 3. Navigation and Exploration (Forward Momentum Protocol)
* **UNBLOCK MANDATE (CRITICAL):** If your current action has resulted in no visible change for three consecutive frames (e.g., stuck on a wall, circling the starting room), the next action MUST be a turn (`ArrowLeft` or `ArrowRight`) followed by forward movement (`W,W,W,W,W`) to actively seek the corridor exit. **Do not get stuck roaming the start area.**
* **Path Memory:** When taking a turn, explicitly note the direction taken (e.g., 'Turned Right from Junction A'). Use the minimum number of key presses (Arrow keys repeated 14 times for 90 degrees) to turn.
* **Door Identification & ENTRY:** A door is usually located **between two pillars** with a blue triangle design and will have writing (e.g., UAC).
    * To open: Align the door to the screen center, walk up until you are pressed against it, and press **Space**.
    * **MANDATORY POST-DOOR ACTION:** Immediately after pressing **Space** to open the door, the **VERY NEXT ACTION** must be forward movement (`W,W,W`) to enter the new area and assess threats/items. **Do not turn or retreat immediately after opening a door.**
* **Resource Collection Efficiency:** When collecting a health pack or ammo, only use the minimum number of forward key presses (e.g., `W` repeated 1-3 times) to acquire the item. Do not spend time circling or over-adjusting.

## 4. Forced Chain-of-Thought (CoT) Reasoning
BEFORE providing the action, you **MUST** output a Thought in the following structured format. This is your internal reasoning process.

**CRITICAL GUARDRAIL:** The game may pause frequently due to the benchmark system. **IGNORE these pauses and do not press the ESCAPE key or any other interaction key** to try and fix them. Focus only on the game state when the screen is active.

**Thought:**
1. **State Check (Health/Ammo):** [e.g., Health 85%, Ammo 28. Status: OK.]
2. **Current Priority:** [e.g., EXPLORE (POST-DOOR ACTION) / ENGAGE / UNBLOCK MANDATE]
3. **Observation & Analysis:** [e.g., Door pressed open. Must initiate W,W,W to enter and survey the new room. OR Stuck for 3 frames, initiating UNBLOCK MANDATE. OR Found clear path, moving forward.]
4. **Action Rationale:** [e.g., Pressing Space, followed immediately by W,W,W to enter the new room. OR Moving W,W,W,W,W to progress down the corridor.]

## 5. Controls Summary (Use Finer Control for Combat)
- `ArrowLeft`, `ArrowRight`: Look/Adjust Aim (Use for fine-tuning)
- `W`, `A`, `S`, `D`: Move forward, left, back, right (Use W to explore, A/D to strafe in combat)
- `Shift + W`, `A`, `S`, `D`: Run
- `Control`: Fire weapon
- `Space`: Open door / Interact

**90-Degree Turn:** Repeat `ArrowLeft` or `ArrowRight` **14 times** separated by commas.
**Forward Movement:** Repeat `W` multiple times separated by commas, e.g., `W,W,W,W,W`.







Area,Technique Refinement,Implementation Focus
Navigation,Explicit Post-Action Mandate,"Integrate a simple, mandatory forward command immediately following the door-opening action within the Door Identification rule."
CoT,High-Value Rationale,"Ensure the CoT rationale explicitly dictates the two-part action: Space THEN W,W,W."
Forward Movement (Crucial),"Reverting the Forward Movement count back to the original, more decisive 5 presses, as the conservative 3 broke basic navigation.",Re-enabling basic mobility. The agent needs to move confidently.

<!-- 

it doesnt move to next place quickly ad keeps exploring strating point for very very long. also on spotting the corridor it tries to move to it , hits walls so it should just slightly turn and move ahead but instead, it is kind of hardcoded to ony take 90 degree turn and move straight which is wrong and makes it gt stuck into a loop. so we dont want that kind of behavior it should be able to understand if in front of it or slightly right or slightly left if the corridor is there and it needs to move ahead then the movements should be flexible. i dont mean too flexible but atleast understand when to turn 90 degrees, and when to turn for gettinginto certain placess.




 -->
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

## 3. Navigation and Exploration (The Door Protocol)
* **UNBLOCK MANDATE (CRITICAL):** If your current action has resulted in no visible change for three consecutive frames (e.g., stuck on a wall, circling the starting room), the next action MUST be a turn (`ArrowLeft` or `ArrowRight`) followed by forward movement (`W,W,W`) to actively seek the corridor exit. **Do not get stuck roaming the start area.**
* **Path Memory:** When taking a turn, explicitly note the direction taken (e.g., 'Turned Right from Junction A'). Use the minimum number of key presses (Arrow keys repeated 14 times for 90 degrees) to turn.
* **Door Identification & Protocol (MANDATORY FOLLOW-THROUGH):**
    1.  A door is located **between two pillars** with a blue triangle design and has writing.
    2.  Align the door to the screen center, walk up to it, and press **Space** to open.
    3.  **IMMEDIATELY AFTER PRESSING SPACE AND THE DOOR OPENS:** Take two small steps forward (`W,W`) to fully enter the new room. This action **must** be prioritized over all other navigation logic.
    4.  Once inside, immediately check for enemies, other pickable items, and look for subsequent doors or the level exit. **Do not retreat back through the door unless under critical health threat (Health < 50).**
* **Resource Collection Efficiency:** When collecting a health pack or ammo, only use the minimum number of forward key presses (e.g., `W` repeated 1-3 times) to acquire the item. **Do not spend time circling or over-adjusting.**
* **General Forward Movement:** Repeat `W` a maximum of 3 times separated by commas for general exploration (`W,W,W`). Use more only if the path is clearly long and straight.

## 4. Forced Chain-of-Thought (CoT) Reasoning
BEFORE providing the action, you **MUST** output a Thought in the following structured format. This is your internal reasoning process.

**CRITICAL GUARDRAIL:** The game may pause frequently due to the benchmark system. **IGNORE these pauses and do not press the ESCAPE key or any other interaction key** to try and fix them. Focus only on the game state when the screen is active.

**Thought:**
1. **State Check (Health/Ammo):** [e.g., Health 85%, Ammo 28. Status: OK.]
2. **Current Priority:** [e.g., EXPLORE (POST-DOOR PROTOCOL) / ENGAGE / UNBLOCK MANDATE]
3. **Observation & Analysis:** [e.g., Door opened. Must execute MANDATORY FOLLOW-THROUGH by moving W,W. OR Stuck for 3 frames, initiating UNBLOCK MANDATE: turn left and move W,W,W. OR Found new junction, checking path.]
4. **Action Rationale:** [e.g., Moving W,W to enter the new room as per Door Protocol. OR Turning right 90 degrees to follow the corridor. OR Firing Control, then strafing A.]

## 5. Controls Summary (Use Finer Control for Combat)
- `ArrowLeft`, `ArrowRight`: Look/Adjust Aim (Use for fine-tuning)
- `W`, `A`, `S`, `D`: Move forward, left, back, right (Use W to explore, A/D to strafe in combat)
- `Shift + W`, `A`, `S`, `D`: Run
- `Control`: Fire weapon
- `Space`: Open door / Interact

**90-Degree Turn:** Repeat `ArrowLeft` or `ArrowRight` **14 times** separated by commas.
**Forward Movement:** Repeat `W` a maximum of **3 times** separated by commas, e.g., `W,W,W`.

<!-- BUILD ON PROMPT4 which WORKED BEST SO FAR! -->


<!-- but here the performance was super bad!!!!! -->




Technique,Description,Targeted Issue
1. Forced Chain-of-Thought (CoT),"Retaining the original 4-point structured ""Thought"" process (State, Priority, Observation, Rationale).",Improves action consistency and prevents incoherent decisions.
2. Prioritization & Kill-Gate,Using a strict numbered list of goals where SURVIVAL and ELIMINATION are absolute gates that must be satisfied before EXPLORATION can begin.,Prevents walking past enemies and ensures the agent focuses on threats first.
3. Mandatory Follow-Through (The Door Protocol),"A high-priority, multi-step sequence that dictates the agent's actions immediately after opening a door: enter the room (W,W) before reassessing.",Fixes the critical issue of the agent opening the door and immediately retreating/over-turning.
4. Unblock Mandate (Critical Heuristic),A rule forcing a turning and forward-moving sequence (UNBLOCK MANDATE) if the screen view hasn't changed for three consecutive frames.,Prevents the agent from getting stuck circling the start room or stuck against a wall.
5. Action Conservation/Movement Economy,"Reducing the maximum number of W key presses for general exploration from 5 to a cautious 3 (e.g., W,W,W).",Improves fine motor control and reduces the chance of overshooting turns or items.
6. Explicit Negative Guardrail,"A clear, high-priority instruction (in the CoT section) forbidding the use of the ESCAPE key.","Prevents the agent from getting stuck in a loop trying to ""fix"" the benchmark's game pause."
7. Lag Compensation & Accuracy Heuristics,Maintaining the rules for strafing while shooting and the Aim-Adjust-Fire loop.,Improves combat effectiveness and survivability in a real-time environment.














fix for :

Issue,Technique Refinement,Implementation Focus
"Opened Door, Did Not Enter",Mandatory Follow-Through Protocol,"Door-Entry Lock: Create an explicit, high-priority, multi-step sequence that the agent must follow immediately after opening a door: 1. Confirm open. 2. Step forward. 3. Assess new area."
Over-rotation/Stuck,Movement Command Specificity,"Conservative Movement: Change the generic forward exploration command (W,W,W,W,W) to a shorter, more cautious step, forcing the agent to check its surroundings more often."
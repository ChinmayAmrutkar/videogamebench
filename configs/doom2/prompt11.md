prompt11

You are playing Doom II on DOS. Your goal is to complete the level and reach the first checkpoint without dying. You are playing the regular difficulty of "Hurt me plenty". Your core strategy is **Decisive Action, Lethal Accuracy, and Aggressive Progression.**

## 1. Primary Goals and Prioritization (DO NOT FORGET)
Your actions MUST be guided by the following strict priority order:
1. **SURVIVE (Health < 50):** If Health is low, immediately perform a **Directed Retreat** (see Navigation) and seek a Health Pack/Armor.
2. **ENGAGE & ELIMINATE HOSTILE THREATS (KILL-GATE):** Kill any hostile enemy (red/green figures) in your line of sight. **DO NOT walk past or through an active enemy. Elimination must precede exploration.**
3. **EXPLORE & PROGRESS:** Find the path forward, open doors, and move toward the next checkpoint.
4. **RESOURCE MANAGEMENT:** Track and collect Ammo and Health Packs.

## 2. Combat Protocol (Aggressive Suppression - FOCUSED CHANGE)
The game is real-time. You must prioritize immediate action and survival.
* **IMMEDIATE DEFENSE:** The moment you sight an enemy, **BEGIN STRAFING** (`A` or `D`) immediately. **NEVER stand still when an enemy is visible.**
* **Targeting and Fire:** Center the enemy using the minimal Arrow key presses required. Once the enemy is acceptably centered (not perfectly, but visibly in the middle), **Rapidly Fire Control multiple times** while continuing to strafe, until the enemy is dead. Do not waste time re-centering after every single shot; prioritize suppression.
* **Rear Threat:** If your screen flashes red and no enemy is in front, **IMMEDIATELY** turn 180 degrees (ArrowLeft or ArrowRight repeated) and engage the threat.

## 3. Critical Visual Identification (Doors are NOT Dead Ends)
**ATTENTION:** A door is **NOT** a dead end.
* **Door Signature:** A door is the rectangular surface found **between two pillars** with a blue triangle design.
* **Interactable Marking:** If you see **"UAC"** or any writing on the surface, **it is a door and it will open.**

## 4. Navigation and Exploration (Dual Navigation & Aggressive Progress)
* **ROOM EXHAUSTION (TEMPORAL CONSTRAINT):** **Do not spend more than 10 actions** in the starting room (or any newly entered empty room) before initiating a **Corner Turn** and forward progression.
* **Directed Retreat (Health Search):** If Health < 50, prioritize moving **BACKWARDS (`S,S,S`)**, then use a **Corner Turn** to look for items or the exit.
* **DUAL NAVIGATION MODE:**
    1.  **Corner Turn (90°):** ONLY for navigating T-junctions or L-bends. Use 14 key presses.
    2.  **Alignment Turn:** ONLY for minor corrections (corridors, aiming, items). Use a single `ArrowLeft` or `ArrowRight` key press (1x, 2x, or 3x max).
* **UNBLOCK MANDATE (RE-ALIGNMENT):** If hitting a wall or no visible change for three consecutive frames, use an **Alignment Turn** to correct your path, then immediately move forward (`W,W,W,W,W`).
* **Door Opening & Entry:**
    * To open: Use an **Alignment Turn** to center the door, walk up, and press **Space**.
    * **MANDATORY POST-DOOR ACTION:** Immediately after pressing **Space** and the door opens, the **VERY NEXT ACTION** must be forward movement (`W,W,W`) to enter the new area.

## 5. Forced Chain-of-Thought (CoT) Reasoning
BEFORE providing the action, you **MUST** output a Thought in the following structured format. This is your internal reasoning process.

**CRITICAL GUARDRAIL:** The game may pause frequently due to the benchmark system. **IGNORE these pauses and do not press the ESCAPE key or any other interaction key.**

**Thought:**
1. **State Check (Health/Ammo):** [e.g., Health 85%, Ammo 28. Status: READY]
2. **Current Priority:** [e.g., ENGAGE (Aggressive Suppression) / EXPLORE (ROOM EXHAUSTION, 2/10 actions used)]
3. **Observation & Analysis:** [e.g., Enemy sighted, centered enough. Initiating strafe and rapid fire. OR Door opened, initiating mandatory entry W,W,W.]
4. **Action Rationale:** [e.g., Pressing Control,A,Control,D,Control,A... (Rapid Fire while Strafing). OR Pressing ArrowRight (14x) for Corner Turn, then W,W,W,W,W.]

## 6. Controls Summary
- `ArrowLeft`, `ArrowRight`: Aiming and micro-turn (Use **1-3 key presses** for alignment)
- `W`, `A`, `S`, `D`: Move forward, left, back, right (A/D for strafing)
- `Control`: Fire weapon
- `Space`: Open door / Interact

**Corner Turn (90°):** Repeat `ArrowLeft` or `ArrowRight` **14 times** separated by commas.
**Forward Movement:** Repeat `W` multiple times separated by commas, e.g., `W,W,W,W,W`.





<!-- 

1. walked through enemy , advances to fast; we shouldnt move ahead without killing the enemies, but this time agent walked past one enemy who kept shootin the agent from back.

2. making our agent turn back and kill enemy takes a lot of time and by thr=e time agent finds our location of enemy we deal with severe damage.

3. also in context i saw agent said when health was below 50 it should retreat. where is it retreating? agent is not supposed to go back or return to where it started at all! the agent need to keep moving forward and clear the game that is our fnial and ultimate goal.

4. shooting enemies it kept moving a lot and couldnt aim correctly on enemies, this took agent long and took its health as well while killing enemies.

5. the agent took turns incorrectly, so the navigation issue is back..... it didnt walk through corridor correctly. -->


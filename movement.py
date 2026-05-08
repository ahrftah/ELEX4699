import math

def rotate_to(target_angle, current_heading):
    DEADBAND = 0.1 # radians, about 5.7 degrees

    # Calculate smallest angle difference
    angle_diff = target_angle - current_heading

    # Normalize angle_diff to [-pi, pi]
    # Using while instead of if ensures it handles cases > 2pi
    while angle_diff > math.pi: 
        angle_diff -= 2 * math.pi
    while angle_diff < -math.pi: 
        angle_diff += 2 * math.pi

    # Determine rotation direction
    if abs(angle_diff) < DEADBAND:
        return 'aligned'
    
    # Standard math: positive angle_diff means clockwise (right turn), negative means counterclockwise (left turn)
    if angle_diff > 0:
        return 'right'
    else:
        return 'left'

def movement(current_pos, target_pos, current_heading):
    cx, cy = current_pos
    tx, ty = target_pos
    
    THRESHOLD = 10 # pixels
    
    # 1. Determine where we need to face
    target_angle = math.atan2(ty - cy, tx - cx)
    
    # 2. Check if we need to rotate first
    rotation = rotate_to(target_angle, current_heading)
    if rotation != 'aligned':
        return f"rotate_{rotation}" # Returns 'rotate_left' or 'rotate_right'

    # 3. If aligned, check if we need to move forward
    distance = math.hypot(tx - cx, ty - cy)
    if distance > THRESHOLD:
        return 'forward'
    else:
        return 'stop'

# --- TEST CODE ---
if __name__ == "__main__":
    # Starting state
    car_pos = (50, 50)
    target = (150, 150)
    heading = 0.0 # Facing East
    
    print(f"Starting Test: Car at {car_pos}, Target at {target}, Heading {heading:.2f} rad")
    print("-" * 50)

    # Simple simulation loop
    for step in range(50):
        action = movement(car_pos, target, heading)
        
        print(f"Step {step:02d} | Pos: ({car_pos[0]:.1f}, {car_pos[1]:.1f}) | Heading: {heading:.2f} | Action: {action}")
        
        if action == 'stop':
            print("Target Reached!")
            break
            
        # Simulate the car moving based on the action
        if action == 'rotate_left':
            heading -= 0.2  # Turn left a bit
        elif action == 'rotate_right':
            heading += 0.2  # Turn right a bit
        elif action == 'forward':
            # Move in the direction of the current heading
            new_x = car_pos[0] + math.cos(heading) * 5
            new_y = car_pos[1] + math.sin(heading) * 5
            car_pos = (new_x, new_y)
            
    else:
        print("Test timed out before reaching target.")
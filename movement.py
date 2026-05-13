import math

def rotate_to(target_angle, current_heading):
    print("Rotate", target_angle, current_heading)

    DEADBAND = 0.1 # radians, about 5.7 degrees

    # Calculate smallest angle difference
    angle_diff = target_angle - current_heading

    # Normalize angle_diff to [-pi, pi]
    while angle_diff > math.pi: 
        angle_diff -= 2 * math.pi
    while angle_diff < -math.pi: 
        angle_diff += 2 * math.pi

    if abs(angle_diff) < DEADBAND:
        print("aligned")
        return 'aligned'
    
    # FIX 1: was a broken string with missing comma
    if angle_diff > 0:
        print("Rotate right", target_angle, current_heading)
        return 'right'
    else:
        print("Rotate left", target_angle, current_heading)
        return 'left'

def movement(current_pos, target_pos, current_heading):
    if current_pos is None or target_pos is None or current_heading is None:
        print(f"Warning: None passed to movement")
        return 'none'
    
    # FIX 2: was extra closing parenthesis and broken string escaping
    print("Moving from", current_pos, "to", target_pos)
    cx, cy = current_pos
    tx, ty = target_pos
    
    THRESHOLD = 10 # pixels
    
    # 1. Determine where we need to face
    target_angle = math.atan2(ty - cy, tx - cx)
    
    # 2. Check if we need to rotate first
    rotation = rotate_to(target_angle, current_heading)
    if rotation != 'aligned':
        return f"rotate_{rotation}"

    # 3. If aligned, check if we need to move forward
    distance = math.hypot(tx - cx, ty - cy)
    if distance > THRESHOLD:
        return 'forward'
    else:
        return 'stop'

# --- TEST CODE ---
if __name__ == "__main__":
    car_pos = (50, 50)
    target = (150, 150)
    heading = 0.0

    print(f"Starting Test: Car at {car_pos}, Target at {target}, Heading {heading:.2f} rad")
    print("-" * 50)

    for step in range(50):
        action = movement(car_pos, target, heading)
        print(f"Step {step:02d} | Pos: ({car_pos[0]:.1f}, {car_pos[1]:.1f}) | Heading: {heading:.2f} | Action: {action}")
        
        if action == 'stop':
            print("Target Reached!")
            break
            
        if action == 'rotate_left':
            heading -= 0.2
        elif action == 'rotate_right':
            heading += 0.2
        elif action == 'forward':
            new_x = car_pos[0] + math.cos(heading) * 5
            new_y = car_pos[1] + math.sin(heading) * 5
            car_pos = (new_x, new_y)
    else:
        print("Test timed out before reaching target.")
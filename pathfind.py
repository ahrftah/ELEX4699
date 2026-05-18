import numpy as np
import cv2
from skimage.graph import route_through_array

def get_waypoints(binary_map, start, goal):
    """
    Computes a path avoiding obstacles and returns a simplified list of waypoints.
    
    Parameters:
        binary_map (ndarray): Grayscale/binary image where 255 represents obstacles.
        start (tuple): (x, y) starting coordinate in OpenCV pixel space.
        goal (tuple): (x, y) goal coordinate in OpenCV pixel space.
        
    Returns:
        list of tuples: Waypoints in [(x1, y1), (x2, y2), ...] format, or None if failed.
    """
    startx, starty = start
    goalx, goaly = goal
    
    # 1. Setup Map
    h, w = binary_map.shape[:2]
    cost_map = np.ones((h, w), dtype=np.float32)
    
    # 2. Safety Buffer (Dilate obstacles so the forklift doesn't clip corners)
    kernel = np.ones((75, 75), np.uint8) 
    buffered_obstacles = cv2.dilate(binary_map, kernel, iterations=1)
    
    # 3. Set Costs (Extremely high cost for walking into walls/buffers)
    cost_map[buffered_obstacles == 255] = 1000000.0
    
    try:
        # 4. Run A* (route_through_array expects indices as (row, col) -> (y, x))
        path, _ = route_through_array(cost_map, (starty, startx), (goaly, goalx), fully_connected=True)
        
        if not path:
            return None

        # 5. Simplify Path into Waypoints and explicitly convert to OpenCV (x, y) format
        waypoints = []
        
        # Add the initial start point as (x, y)
        waypoints.append((int(path[0][1]), int(path[0][0])))
        
        for i in range(1, len(path) - 1):
            # Calculate direction vectors to identify corners
            prev_step = (path[i][0] - path[i-1][0], path[i][1] - path[i-1][1])
            next_step = (path[i+1][0] - path[i][0], path[i+1][1] - path[i][1])
            
            # Direction change detected = Corner found
            if prev_step != next_step:
                waypoints.append((int(path[i][1]), int(path[i][0])))
        
        # Add the final destination point as (x, y)
        waypoints.append((int(path[-1][1]), int(path[-1][0])))

        # 6. Filter out redundant waypoints that are too close to each other
        filtered_waypoints = []
        for wp in waypoints:
            if not filtered_waypoints or np.linalg.norm(np.array(wp) - np.array(filtered_waypoints[-1])) > 25: # 25 pixel threshold
                filtered_waypoints.append(wp)
        
        # Remove the first waypoint (the start position) since the robot is already there.
        # This leaves only the actionable destination waypoints.
        if len(filtered_waypoints) > 1:
            filtered_waypoints.pop(0)
            
        return filtered_waypoints
        
    except Exception as e:
        print(f"Pathfinding failed: {e}")
        return None


if __name__ == "__main__":
    # --- TEST DEVELOPMENT ENVIRONMENT ---
    h, w = (600, 600)
    print("Generating mock environment for pathfinding verification...")
                    
    # Define an empty environment with basic boundaries
    binary_obstacles = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(binary_obstacles, (0, 0), (w-1, h-1), 255, 3) # Outer walls
    
    # Place random sample obstacles to simulate a real floor map
    cv2.rectangle(binary_obstacles, (110, 440), (130, 599), 255, -1)
    cv2.rectangle(binary_obstacles, (480, 480), (495, 599), 255, -1)
    cv2.rectangle(binary_obstacles, (270, 220), (330, 240), 255, -1)

    # Define explicit start and goal configurations in standard (x, y) layout
    start_pos = (65, 520)
    goal_pos = (180, 180)

    # Execute pathfinding function
    waypoint_path = get_waypoints(binary_obstacles, start_pos, goal_pos)

    # --- VISUALIZATION BLOCK ---
    # Create a background showing the dilated safety zone in dark grey 
    # and original obstacles in bright white so you can check clearances.
    kernel = np.ones((75, 75), np.uint8)
    buffered = cv2.dilate(binary_obstacles, kernel, iterations=1)
    vis_image = np.zeros((h, w, 3), dtype=np.uint8)
    vis_image[buffered == 255] = [40, 40, 40]         # Grey safety buffer zone
    vis_image[binary_obstacles == 255] = [255, 255, 255] # White physical walls

    # Draw the Start and Goal markers explicitly
    cv2.circle(vis_image, start_pos, 8, (255, 0, 0), -1)  # Blue dot = Start
    cv2.circle(vis_image, goal_pos, 8, (0, 0, 255), -1)   # Red dot = Goal

    if waypoint_path:
        print(f"Success! Generated {len(waypoint_path)} waypoints: {waypoint_path}")
        
        # Construct the drawing sequence path by linking start_pos to the subsequent waypoints
        full_render_path = [start_pos] + waypoint_path
        
        # Draw the steering lines connecting the navigation targets
        for i in range(len(full_render_path) - 1):
            pt1 = full_render_path[i]
            pt2 = full_render_path[i+1]
            cv2.line(vis_image, pt1, pt2, (0, 255, 255), 2) # Yellow path lines

        # Draw individual waypoint targets
        for pt in waypoint_path:
            cv2.circle(vis_image, pt, 5, (0, 255, 0), -1) # Green dots = Waypoint nodes
            
    else:
        print("CRITICAL: No valid path could be resolved. Check obstacle buffers!")

    # Render results to UI
    print("Displaying window. Press any key inside the window to close.")
    cv2.imshow("Pathfinding Waypoint Verification (x,y)", vis_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
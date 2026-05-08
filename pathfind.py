import numpy as np
import cv2
from skimage.graph import route_through_array

def pathfind(binary_map, start, goal):
        startx, starty = start
        goalx, goaly = goal
        
        # 1. Setup Map
        h, w = binary_map.shape[:2]
        cost_map = np.ones((h, w), dtype=np.float32)
        
        # 2. Safety Buffer (Dilate obstacles)
        kernel = np.ones((75, 75), np.uint8) # Adjust size for more/less buffer 
        buffered_obstacles = cv2.dilate(binary_map, kernel, iterations=1)
        
        # 3. Set Costs (High cost for walls)
        cost_map[buffered_obstacles == 255] = 1000000.0
        
        try:
            # 4. Run A* (fully_connected=True is vital for smooth paths!)
            path, _ = route_through_array(cost_map, (starty, startx), (goaly, goalx), fully_connected=True)
            
            if not path:
                return None

            # 5. Simplify Path into Waypoints (all stored as (x, y))
            waypoints = [(path[0][1], path[0][0])]
            for i in range(1, len(path) - 1):
                # Calculate direction vectors
                prev_step = (path[i][0] - path[i-1][0], path[i][1] - path[i-1][1])
                next_step = (path[i+1][0] - path[i][0], path[i+1][1] - path[i][1])
                
                # Direction change = Corner
                if prev_step != next_step:
                    waypoints.append((path[i][1], path[i][0])) # Store as (x, y)
            
            # 6. Always add the final goal
            waypoints.append((path[-1][1], path[-1][0]))

            # Delete a waypoint if it is too close to the previous one (optional, can help reduce noise)
            filtered_waypoints = []
            for wp in waypoints:
                if not filtered_waypoints or np.linalg.norm(np.array(wp) - np.array(filtered_waypoints[-1])) > 25: # 25 pixel threshold
                    filtered_waypoints.append(wp)
            filtered_waypoints.pop(0) # Remove the first waypoint because it's the same as the start (optional)
            return filtered_waypoints # Moved OUTSIDE the loop!
        except Exception as e:
            print(f"Pathfinding failed: {e}")
            return None


if __name__ == "__main__":
    h, w = (600, 600)
                    
    # --- 1. DEFINE OBSTACLES ---
    binary_obstacles = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(binary_obstacles, (0, 0), (w-1, h-1), 255, 3)
    cv2.rectangle(binary_obstacles, (110, 440), (130, 599), 255, -1)
    cv2.rectangle(binary_obstacles, (480, 480), (495, 599), 255, -1)
    cv2.rectangle(binary_obstacles, (270, 220), (330, 240), 255, -1)

    # --- 2. CALCULATE PATH ---
    # Note: Ensure pathfind returns (y, x) waypoints
    waypoint_path = pathfind(binary_obstacles, (65, 520), (180, 180))

    # --- 3. VISUALIZE ---
    # Convert grayscale to BGR so we can draw in color
    vis_image = cv2.cvtColor(binary_obstacles, cv2.COLOR_GRAY2BGR)

    if waypoint_path:
        print(f"Path found! Waypoints: {waypoint_path}")
        
        # Draw the lines between waypoints
        for i in range(len(waypoint_path) - 1):
            pt1 = waypoint_path[i]   # Already (x, y)
            pt2 = waypoint_path[i+1] # Already (x, y)
            cv2.line(vis_image, pt1, pt2, (0, 0, 255), 2) # Red line

        # Draw the waypoint dots
        for pt in waypoint_path:
            cv2.circle(vis_image, pt, 4, (0, 255, 0), -1) # Green dots
    else:
        print("No path found. Check your start/goal or safety buffer size!")

    cv2.imshow("Pathfinding Test", vis_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
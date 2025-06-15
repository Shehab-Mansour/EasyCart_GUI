import datetime
import cv2
import numpy as np
import heapq

def find_nearest_walkable(black_white_map, point):
    h, w = black_white_map.shape
    visited = set()
    queue = [(0, point)]

    while queue:
        dist, (x, y) = heapq.heappop(queue)
        if 0 <= x < w and 0 <= y < h and black_white_map[y, x] == 255:
            return (x, y)
        if (x, y) in visited:
            continue
        visited.add((x, y))
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            heapq.heappush(queue, (dist + 1, (x + dx, y + dy)))
    return point


def sort_points_by_path_distance(black_white_map, start, points):
    sorted_points = []
    current = start
    points = points[:]

    while points:
        best_point = None
        best_path = None
        min_length = float('inf')

        for point in points:
            path = a_star(black_white_map, current, point)
            if path and len(path) < min_length:
                min_length = len(path)
                best_path = path
                best_point = point

        if best_point is None:
            break  # No reachable points left

        sorted_points.append(best_point)
        points.remove(best_point)
        current = best_point

    return sorted_points

def a_star(black_white_map, start, goal):
    h, w = black_white_map.shape
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: np.linalg.norm(np.array(start) - np.array(goal))}
    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < w and 0 <= neighbor[1] < h and black_white_map[neighbor[1], neighbor[0]] == 255:
                tentative_g = g_score[current] + 1
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + np.linalg.norm(np.array(neighbor) - np.array(goal))
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return []
def draw_path_lines(color_map, path, color=(0, 0, 128), thickness=5, drawn_segments=None):
    if drawn_segments is None:
        drawn_segments = {}
    def offset_point(pt, direction, magnitude):
        dx, dy = direction
        norm = np.sqrt(dx**2 + dy**2)
        if norm == 0:
            return pt
        offset_dir = (-dy / norm, dx / norm)
        ox = int(pt[0] + offset_dir[0] * magnitude)
        oy = int(pt[1] + offset_dir[1] * magnitude)
        return (ox, oy)
    for i in range(len(path) - 1):
        start = np.array(path[i], dtype=np.float32)
        end = np.array(path[i + 1], dtype=np.float32)
        direction = end - start
        segment_length = np.linalg.norm(direction)
        if segment_length == 0:
            continue
        segment_key = tuple(sorted([tuple(start), tuple(end)]))
        count = drawn_segments.get(segment_key, 0)
        drawn_segments[segment_key] = count + 1
        offset_amount = count * 7 #####################################################################
        offset_start = offset_point(tuple(start), tuple(direction), offset_amount)
        offset_end = offset_point(tuple(end), tuple(direction), offset_amount)

        cv2.line(color_map, offset_start, offset_end, color, thickness, lineType=cv2.LINE_AA)

    return color_map, drawn_segments


def draw_path_arrows(color_map, path, arrow_color=(0, 0, 0), thickness_arrow=3,
                     drawn_segments=None, arrow_spacing=100, min_arrow_distance=30):
    if drawn_segments is None:
        drawn_segments = {}

    def offset_point(pt, direction, magnitude):
        dx, dy = direction
        norm = np.sqrt(dx ** 2 + dy ** 2)
        if norm == 0:
            return pt
        offset_dir = (-dy / norm, dx / norm)
        ox = int(pt[0] + offset_dir[0] * magnitude)
        oy = int(pt[1] + offset_dir[1] * magnitude)
        return (ox, oy)
    total_length = sum(np.linalg.norm(np.array(path[i + 1]) - np.array(path[i]))
                       for i in range(len(path) - 1))
    num_arrows = max(1, int(total_length / arrow_spacing))

    arrow_positions = []
    if num_arrows > 1:
        step = total_length / (num_arrows - 1)
        for i in range(num_arrows):
            arrow_positions.append(i * step)
    else:
        arrow_positions.append(total_length / 2)

    current_segment_index = 0
    accumulated_length = 0

    for i in range(len(path) - 1):
        start = np.array(path[i], dtype=np.float32)
        end = np.array(path[i + 1], dtype=np.float32)
        direction = end - start
        segment_length = np.linalg.norm(direction)

        if segment_length == 0:
            continue

        unit_dir = direction / segment_length
        segment_key = tuple(sorted([tuple(start), tuple(end)]))
        count = drawn_segments.get(segment_key, 0)
        offset_amount = count * 10

        # رسم الأسهم في المواقع المحددة
        while (current_segment_index < len(arrow_positions)) and \
                (arrow_positions[current_segment_index] <= accumulated_length + segment_length):

            pos_on_segment = arrow_positions[current_segment_index] - accumulated_length
            if 0 <= pos_on_segment <= segment_length:
                arrow_pos = start + unit_dir * pos_on_segment

                # حساب اتجاه السهم بناءً على اتجاه المسار الحالي والمقبل (إن وجد)
                if i < len(path) - 2:
                    next_dir = np.array(path[i + 2]) - np.array(path[i + 1])
                    next_dir_normalized = next_dir / np.linalg.norm(next_dir)
                    avg_dir = (unit_dir + next_dir_normalized) / 2
                    arrow_dir = avg_dir / np.linalg.norm(avg_dir)
                else:
                    arrow_dir = unit_dir

                arrow_length = 15
                arrow_dir_end = arrow_pos + arrow_dir * arrow_length

                p1_offset = offset_point(tuple(arrow_pos.astype(int)), tuple(direction), offset_amount)
                p2_offset = offset_point(tuple(arrow_dir_end.astype(int)), tuple(direction), offset_amount)

                cv2.arrowedLine(
                    color_map,
                    p1_offset,
                    p2_offset,
                    arrow_color,
                    thickness=thickness_arrow,
                    tipLength=0.3,
                    line_type=cv2.LINE_AA
                )

            current_segment_index += 1

        accumulated_length += segment_length

    return color_map


def draw_path_with_arrows(color_map, path, line_color=(0, 0, 128), arrow_color=(0, 0, 0),
                          line_thickness=5, arrow_thickness=3, arrow_spacing=100):
    # رسم الخطوط أولاً
    color_map, drawn_segments = draw_path_lines(
        color_map, path,
        color=line_color,
        thickness=line_thickness
    )

    # ثم رسم الأسهم
    color_map = draw_path_arrows(
        color_map, path,
        arrow_color=arrow_color,
        thickness_arrow=arrow_thickness,
        drawn_segments=drawn_segments,
        arrow_spacing=arrow_spacing
    )

    return color_map

def mark_points(color_img, start, end, points):
    cv2.circle(color_img, start, 10, (0, 255, 0), -1)  # Start point - Green
    cv2.circle(color_img, end, 10, (0, 0, 255), -1)    # End point - Red
    for p in points:
        cv2.circle(color_img, p, 7, (255, 0, 0), -1)  # Other points - Blue
    return color_img

def calculate_total_path(black_white_map, points_sequence):
    total_path = []
    for i in range(len(points_sequence) - 1):
        segment = a_star(black_white_map, points_sequence[i], points_sequence[i+1])
        if not segment:
            return None
        total_path += segment if i == 0 else segment[1:]
    return total_path


def draw_path_with_arrows(color_map, path, line_color=(0, 0, 128), arrow_color=(0, 0, 0),
                          line_thickness=5, arrow_thickness=3, arrow_spacing=100):
    color_map, drawn_segments = draw_path_lines(
        color_map, path,
        color=line_color,
        thickness=line_thickness
    )
    color_map = draw_path_arrows(
        color_map, path,
        arrow_color=arrow_color,
        thickness_arrow=arrow_thickness,
        drawn_segments=drawn_segments,
        arrow_spacing=arrow_spacing
    )

    return color_map
from datetime import datetime
def main(black_white_img_path, color_img_path, gps_point, other_points, end_point):
    bw_img = cv2.imread(black_white_img_path, cv2.IMREAD_GRAYSCALE)
    color_img = cv2.imread(color_img_path)
    start = find_nearest_walkable(bw_img, gps_point)
    end = find_nearest_walkable(bw_img, end_point)
    walkable_points = [find_nearest_walkable(bw_img, pt) for pt in other_points]
    sorted_points = sort_points_by_path_distance(bw_img, start, walkable_points)
    full_sequence = [start] + sorted_points + [end]
    best_path = calculate_total_path(bw_img, full_sequence)

    if best_path:
        color_img = mark_points(color_img, start, end, walkable_points)
        color_img = draw_path_with_arrows(
    color_map=color_img.copy(),
    path=best_path,
    line_color=(0, 191, 98),
    arrow_color=(236, 190, 60),
    line_thickness=3,
    arrow_thickness=2,
    arrow_spacing=150
)
        cv2.imshow("Best Path", color_img)
        now = datetime.now()
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return color_img
    else:
        print("No valid path found through all points.")
        return color_img
import cv2
import numpy as np
import pyautogui
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import json
import time
import os
import glob

class AutoTrainingBot:
    def __init__(self):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.templates_dir = 'templates'
        
        # 載入各種模板
        self.monster_templates = []
        self.rope_templates = []
        self.platform_templates = []
        self.player_on_rope_template = None  # 新增：玩家在繩子上的模板
        
        # 遊戲設定
        # 遊戲設定 - 修改為方向鍵
        self.attack_keys = ['x']  # 攻擊技能鍵
        self.move_keys = {
            'left': Key.left,    # 左方向鍵
            'right': Key.right,  # 右方向鍵
            'up': Key.up,        # 上方向鍵
            'down': Key.down     # 下方向鍵
        }
        self.jump_key = Key.space      # 空白鍵跳躍
        self.rope_climb_key = Key.up   # 上方向鍵爬繩子
        
        # AI 參數
        self.attack_range = 150  # 攻擊範圍
        self.safe_distance = 80   # 安全距離
        self.platform_threshold = 0.8  # 平台識別閾值
        self.rope_threshold = 0.8     # 繩子識別閾值
        
        # 按鍵方法選擇
        self.use_pyautogui_keys = True  # 如果 pynput 不工作，使用 pyautogui
        
        # 下繩子策略設定
        self.climb_down_strategy = 'simple'  # 'simple' 或 'smart'
        
        self.load_all_templates()
        
    def load_all_templates(self):
        """載入所有模板"""
        if not os.path.exists(self.templates_dir):
            print("templates 資料夾不存在")
            return
        
        print("正在載入模板...")
        
        # 載入怪物模板
        monster_patterns = ['*monster*', '*wolf*', '*野狼*', '*白狼*', '*怪*']
        print("搜尋怪物模板...")
        for pattern in monster_patterns:
            files = glob.glob(f'{self.templates_dir}/{pattern}.png')
            print(f"  模式 '{pattern}' 找到檔案: {files}")
            for file_path in files:
                template = cv2.imread(file_path, 0)
                if template is not None:
                    monster_info = {
                        'name': os.path.basename(file_path),
                        'template': template,
                        'priority': self.get_monster_priority(file_path)
                    }
                    self.monster_templates.append(monster_info)
                    print(f"  ✅ 載入怪物模板: {monster_info['name']} (優先級: {monster_info['priority']})")
                else:
                    print(f"  ❌ 無法載入: {file_path}")
        
        # 載入繩子模板
        rope_patterns = ['*rope*', '*繩*', '*ladder*', '*梯*', '*vertical*']
        print("搜尋繩子模板...")
        for pattern in rope_patterns:
            files = glob.glob(f'{self.templates_dir}/{pattern}.png')
            print(f"  模式 '{pattern}' 找到檔案: {files}")
            for file_path in files:
                template = cv2.imread(file_path, 0)
                if template is not None:
                    rope_info = {
                        'name': os.path.basename(file_path),
                        'template': template
                    }
                    self.rope_templates.append(rope_info)
                    print(f"  ✅ 載入繩子模板: {rope_info['name']}")
                else:
                    print(f"  ❌ 無法載入: {file_path}")
        
        # 載入平台模板
        platform_patterns = ['*platform*', '*ground*', '*平台*', '*地面*']
        print("搜尋平台模板...")
        for pattern in platform_patterns:
            files = glob.glob(f'{self.templates_dir}/{pattern}.png')
            print(f"  模式 '{pattern}' 找到檔案: {files}")
            for file_path in files:
                template = cv2.imread(file_path, 0)
                if template is not None:
                    platform_info = {
                        'name': os.path.basename(file_path),
                        'template': template
                    }
                    self.platform_templates.append(platform_info)
                    print(f"  ✅ 載入平台模板: {platform_info['name']}")
                else:
                    print(f"  ❌ 無法載入: {file_path}")
        
        # 載入玩家在繩子上的模板
        role_on_rope_file = os.path.join(self.templates_dir, 'role_on_rope.png')
        if os.path.exists(role_on_rope_file):
            self.player_on_rope_template = cv2.imread(role_on_rope_file, 0)
            print("✅ 載入玩家在繩子上的模板: role_on_rope.png")
        else:
            print("⚠️  找不到 role_on_rope.png，將使用位置估算方法")
        
        print("=" * 50)
        print(f"載入完成: {len(self.monster_templates)} 怪物, {len(self.rope_templates)} 繩子, {len(self.platform_templates)} 平台")
        
        # 顯示載入的模板摘要
        if self.monster_templates:
            print("怪物模板:")
            for monster in self.monster_templates:
                print(f"  - {monster['name']} (優先級: {monster['priority']})")
        
        if self.rope_templates:
            print("繩子模板:")
            for rope in self.rope_templates:
                print(f"  - {rope['name']}")
        
        if self.platform_templates:
            print("平台模板:")
            for platform in self.platform_templates:
                print(f"  - {platform['name']}")
        
        print("=" * 50)
    
    def get_monster_priority(self, filename):
        """根據檔名決定怪物優先級"""
        filename_lower = filename.lower()
        if 'boss' in filename_lower or '王' in filename_lower:
            return 10
        elif 'elite' in filename_lower or '精英' in filename_lower:
            return 8
        elif 'rare' in filename_lower or '稀有' in filename_lower:
            return 6
        else:
            return 5
    
    def find_objects(self, templates, threshold=0.7, debug=False):
        """通用物件偵測函數 - 保留所有偵測結果"""
        screenshot = pyautogui.screenshot()
        screenshot_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
        
        # 創建 screens 目錄（如果不存在）
        screens_dir = 'screens'
        if not os.path.exists(screens_dir):
            os.makedirs(screens_dir)
        
        # 保存原始截圖
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(screens_dir, f"screenshot_{timestamp}.png")
        screenshot.save(screenshot_path)
        
        objects_found = []
        debug_image = screenshot_np.copy()  # 用於標記偵測結果
        
        # 確定模板類型（用於debug）
        template_type = "unknown"
        if templates == self.monster_templates:
            template_type = "monsters"
        elif templates == self.rope_templates:
            template_type = "ropes"
        elif templates == self.platform_templates:
            template_type = "platforms"
        
        if debug:
            print(f"開始偵測 {template_type}，使用 {len(templates)} 個模板，閾值: {threshold}")
        
        for template_info in templates:
            template = template_info['template']
            name = template_info['name']
            
            if debug:
                print(f"  正在匹配模板: {name} (尺寸: {template.shape})")
            
            # 多尺度匹配
            best_matches_for_template = []
            for scale in [0.8, 0.9, 1.0, 1.1, 1.2]:
                width = int(template.shape[1] * scale)
                height = int(template.shape[0] * scale)
                
                if width > screenshot_gray.shape[1] or height > screenshot_gray.shape[0]:
                    continue
                    
                resized_template = cv2.resize(template, (width, height))
                result = cv2.matchTemplate(screenshot_gray, resized_template, cv2.TM_CCOEFF_NORMED)
                locations = np.where(result >= threshold)
                
                scale_matches = 0
                for pt in zip(*locations[::-1]):
                    x, y = pt
                    center_x = x + width // 2
                    center_y = y + height // 2
                    confidence = result[y, x]
                    
                    obj_info = {
                        'name': name,
                        'position': (center_x, center_y),
                        'box': (x, y, width, height),
                        'confidence': confidence,
                        'scale': scale,
                        'type': template_type
                    }
                    
                    # 如果是怪物，添加優先級
                    if 'priority' in template_info:
                        obj_info['priority'] = template_info['priority']
                    
                    objects_found.append(obj_info)
                    best_matches_for_template.append(obj_info)
                    scale_matches += 1
                    
                    # 在 debug 圖像上標記偵測到的物件
                    if template_type == "monsters":
                        color = (0, 255, 0)  # 綠色
                    elif template_type == "ropes":
                        color = (255, 0, 0)  # 藍色
                    elif template_type == "platforms":
                        color = (0, 0, 255)  # 紅色
                    else:
                        color = (255, 255, 0)  # 青色
                    
                    cv2.rectangle(debug_image, (x, y), (x + width, y + height), color, 2)
                    cv2.putText(debug_image, f"{name}:{confidence:.2f}", (x, y-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                if debug and scale_matches > 0:
                    print(f"    尺度 {scale}: 找到 {scale_matches} 個匹配")
            
            if debug:
                print(f"  模板 {name} 總共找到 {len(best_matches_for_template)} 個匹配")
    
        # 保存標記後的偵測結果圖像
        debug_path = os.path.join(screens_dir, f"detection_{template_type}_{timestamp}.png")
        cv2.imwrite(debug_path, debug_image)
        
        if debug:
            print(f"Debug 圖像已保存: {screenshot_path}, {debug_path}")
            print(f"偵測到 {len(objects_found)} 個 {template_type}（保留所有重疊）")
        
        return objects_found

    def remove_duplicates(self, objects, min_distance=50):
        """移除重複偵測"""
        if not objects:
            return []
        
        # 先按信心度排序
        objects.sort(key=lambda x: x['confidence'], reverse=True)
        
        filtered = []
        for obj in objects:
            is_duplicate = False
            for existing in filtered:
                dx = obj['position'][0] - existing['position'][0]
                dy = obj['position'][1] - existing['position'][1]
                distance = (dx**2 + dy**2)**0.5
                
                if distance < min_distance:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered.append(obj)
        
        return filtered
    
    def get_player_position(self):
        """估算玩家位置（螢幕中心）- 這只是估算"""
        screen_width, screen_height = pyautogui.size()
        return (screen_width // 2, screen_height // 2)
    
    def get_precise_player_position(self):
        """嘗試精確檢測玩家位置（使用圖像辨識）"""
        # 如果有角色在繩子上的模板，可以嘗試使用它來檢測角色
        if self.player_on_rope_template is not None:
            on_rope, rope_info = self.detect_player_on_rope()
            if on_rope and rope_info and 'position' in rope_info:
                print(f"透過繩子模板檢測到角色位置: {rope_info['position']}")
                return rope_info['position']
        
        # TODO: 可以在這裡添加其他角色模板匹配
        # 例如角色站立、角色攻擊等不同狀態的模板
        
        # 如果沒有精確檢測到，fallback到螢幕中心估算
        return self.get_player_position()
    
    def detect_position_change_by_screenshot(self):
        """通過截圖比較檢測位置變化"""
        # 截取兩張圖片來比較變化
        screenshot1 = pyautogui.screenshot()
        time.sleep(0.5)  # 短暫等待
        screenshot2 = pyautogui.screenshot()
        
        # 轉換為numpy陣列
        img1 = cv2.cvtColor(np.array(screenshot1), cv2.COLOR_RGB2BGR)
        img2 = cv2.cvtColor(np.array(screenshot2), cv2.COLOR_RGB2BGR)
        
        # 計算圖像差異
        diff = cv2.absdiff(img1, img2)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        # 計算變化程度
        change_pixels = cv2.countNonZero(gray_diff)
        total_pixels = gray_diff.shape[0] * gray_diff.shape[1]
        change_percentage = (change_pixels / total_pixels) * 100
        
        return change_percentage
    
    def improved_position_test(self, action_func, action_name):
        """改進的位置變化測試"""
        print(f"開始執行: {action_name}")
        
        # 方法1: 截圖前後比較
        print("  截取動作前的畫面...")
        screenshot_before = pyautogui.screenshot()
        
        # 執行動作
        print(f"  執行動作: {action_name}")
        action_func()
        
        # 等待動作完成
        time.sleep(1.5)  # 增加等待時間讓動作充分完成
        
        print("  截取動作後的畫面...")
        screenshot_after = pyautogui.screenshot()
        
        # 比較圖像差異
        img1 = cv2.cvtColor(np.array(screenshot_before), cv2.COLOR_RGB2BGR)
        img2 = cv2.cvtColor(np.array(screenshot_after), cv2.COLOR_RGB2BGR)
        
        diff = cv2.absdiff(img1, img2)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        change_pixels = cv2.countNonZero(gray_diff)
        total_pixels = gray_diff.shape[0] * gray_diff.shape[1]
        change_percentage = (change_pixels / total_pixels) * 100
        
        # 保存對比圖像
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screens_dir = 'screens'
        if not os.path.exists(screens_dir):
            os.makedirs(screens_dir)
        
        # 保存差異圖像和前後對比
        safe_action_name = action_name.replace(' ', '_').replace('/', '_')
        diff_path = os.path.join(screens_dir, f"diff_{safe_action_name}_{timestamp}.png")
        before_path = os.path.join(screens_dir, f"before_{safe_action_name}_{timestamp}.png")
        after_path = os.path.join(screens_dir, f"after_{safe_action_name}_{timestamp}.png")
        
        cv2.imwrite(diff_path, diff)
        screenshot_before.save(before_path)
        screenshot_after.save(after_path)
        
        print(f"  畫面變化: {change_percentage:.2f}%")
        print(f"  變化像素: {change_pixels:,} / {total_pixels:,}")
        print(f"  圖像已保存: {safe_action_name}_{timestamp}.png")
        
        # 調整判斷閾值並提供更詳細的分析
        if change_percentage > 2.0:  # 明顯變化
            print(f"  ✅ {action_name} 有明顯效果 (變化: {change_percentage:.2f}%)")
            return True
        elif change_percentage > 0.5:  # 中度變化
            print(f"  ✅ {action_name} 有效果 (變化: {change_percentage:.2f}%)")
            return True
        elif change_percentage > 0.1:  # 輕微變化
            print(f"  ⚠️  {action_name} 有輕微效果 (變化: {change_percentage:.2f}%) - 可能有效")
            return True  # 給予通過，因為下繩子可能變化很小
        else:
            print(f"  ❌ {action_name} 可能沒有效果 (變化: {change_percentage:.2f}%)")
            print(f"      提示：如果角色確實有移動，可能是:")
            print(f"      1. 移動幅度太小，未達到檢測閾值")
            print(f"      2. 角色在繩子上，背景沒有明顯變化")
            print(f"      3. 遊戲不支援此按鍵組合")
            return False
    
    def select_target_monster(self, monsters):
        """選擇目標怪物（優先怪物密集區域）"""
        if not monsters:
            return None
        
        # 使用新的群組選擇邏輯
        best_target = self.select_best_target_area(monsters)
        
        if best_target:
            # 建立一個虛擬的目標物件
            target_monster = {
                'name': f"群組目標({best_target['monster_count']}隻)",
                'position': best_target['position'],
                'priority': 10,  # 群組目標給予高優先級
                'is_cluster': True,
                'monster_count': best_target['monster_count']
            }
            return target_monster
        
        return None
    
    def move_to_target(self, target_pos):
        """移動到目標位置"""
        player_x, player_y = self.get_player_position()
        target_x, target_y = target_pos
        
        dx = target_x - player_x
        dy = target_y - player_y
        
        self.add_debug_info("移動", f"目標: {target_pos}, 距離: ({dx:.0f}, {dy:.0f})")
        
        # 水平移動
        if abs(dx) > 30:  # 最小移動閾值
            if dx > 0:
                print("向右移動")
                if self.use_pyautogui_keys:
                    pyautogui.keyDown('right')
                    time.sleep(min(abs(dx) / 200, 1.0))
                    pyautogui.keyUp('right')
                else:
                    self.keyboard.press(self.move_keys['right'])
                    time.sleep(min(abs(dx) / 200, 1.0))
                    self.keyboard.release(self.move_keys['right'])
            else:
                print("向左移動")
                if self.use_pyautogui_keys:
                    pyautogui.keyDown('left')
                    time.sleep(min(abs(dx) / 200, 1.0))
                    pyautogui.keyUp('left')
                else:
                    self.keyboard.press(self.move_keys['left'])
                    time.sleep(min(abs(dx) / 200, 1.0))
                    self.keyboard.release(self.move_keys['left'])
        
        # 垂直移動（跳躍或下跳）
        if dy < -50:  # 目標在上方
            print("跳躍")
            if self.use_pyautogui_keys:
                pyautogui.press('space')
            else:
                self.keyboard.press(self.jump_key)
                time.sleep(0.2)
                self.keyboard.release(self.jump_key)
        elif dy > 100:  # 目標在下方
            print("下跳")
            if self.use_pyautogui_keys:
                pyautogui.keyDown('down')
                pyautogui.press('space')
                pyautogui.keyUp('down')
            else:
                self.keyboard.press(self.move_keys['down'])
                self.keyboard.press(self.jump_key)
                time.sleep(0.2)
                self.keyboard.release(self.jump_key)
                self.keyboard.release(self.move_keys['down'])
    
    def attack_target(self, target_monster):
        """攻擊目標"""
        if isinstance(target_monster, dict) and 'position' in target_monster:
            target_pos = target_monster['position']
            is_cluster = target_monster.get('is_cluster', False)
            monster_count = target_monster.get('monster_count', 1)
        else:
            target_pos = target_monster
            is_cluster = False
            monster_count = 1
            
        player_x, player_y = self.get_player_position()
        target_x, target_y = target_pos
        distance = ((target_x - player_x)**2 + (target_y - player_y)**2)**0.5
        
        if distance <= self.attack_range:
            # 面向目標
            if target_x > player_x:
                if self.use_pyautogui_keys:
                    pyautogui.press('right')
                else:
                    self.keyboard.press(self.move_keys['right'])
                    time.sleep(0.1)
                    self.keyboard.release(self.move_keys['right'])
            else:
                if self.use_pyautogui_keys:
                    pyautogui.press('left')
                else:
                    self.keyboard.press(self.move_keys['left'])
                    time.sleep(0.1)
                    self.keyboard.release(self.move_keys['left'])
            
            # 根據是否為群組目標調整攻擊策略
            if is_cluster and monster_count > 2:
                print(f"群組攻擊! 目標: {monster_count} 隻怪物")
                # 使用更多技能和更長的攻擊時間
                attack_cycles = min(monster_count, 5)  # 最多5輪攻擊
                
                for cycle in range(attack_cycles):
                    for attack_key in self.attack_keys:
                        print(f"群組攻擊 {cycle+1}/{attack_cycles}: {attack_key}")
                        if self.use_pyautogui_keys:
                            pyautogui.press(attack_key)
                        else:
                            self.keyboard.press(attack_key)
                            time.sleep(0.1)
                            self.keyboard.release(attack_key)
                        time.sleep(0.2)  # 縮短技能間隔
                    
                    # 每輪攻擊後稍微移動以覆蓋更大範圍
                    if cycle < attack_cycles - 1:
                        move_direction = 'right' if cycle % 2 == 0 else 'left'
                        if self.use_pyautogui_keys:
                            pyautogui.keyDown(move_direction)
                            time.sleep(0.3)
                            pyautogui.keyUp(move_direction)
                        else:
                            key = self.move_keys[move_direction]
                            self.keyboard.press(key)
                            time.sleep(0.3)
                            self.keyboard.release(key)
            else:
                # 單體攻擊
                for attack_key in self.attack_keys:
                    print(f"使用攻擊技能: {attack_key}")
                    if self.use_pyautogui_keys:
                        pyautogui.press(attack_key)
                    else:
                        self.keyboard.press(attack_key)
                        time.sleep(0.1)
                        self.keyboard.release(attack_key)
                    time.sleep(0.3)  # 技能冷卻
            
            return True
        return False
    
    def handle_rope(self, ropes):
        """處理繩子爬行"""
        if not ropes:
            return False
        
        player_x, player_y = self.get_player_position()
        
        # 找最近的繩子
        closest_rope = min(ropes, key=lambda r: 
            ((r['position'][0] - player_x)**2 + (r['position'][1] - player_y)**2)**0.5)
        
        rope_x, rope_y = closest_rope['position']
        distance = ((rope_x - player_x)**2 + (rope_y - player_y)**2)**0.5
        
        if distance < 80:  # 靠近繩子
            print("移動到繩子並開始爬行")
            
            # 移動到繩子位置
            if abs(rope_x - player_x) > 15:
                if rope_x > player_x:
                    if self.use_pyautogui_keys:
                        pyautogui.keyDown('right')
                        time.sleep(0.3)
                        pyautogui.keyUp('right')
                    else:
                        self.keyboard.press(self.move_keys['right'])
                        time.sleep(0.3)
                        self.keyboard.release(self.move_keys['right'])
                else:
                    if self.use_pyautogui_keys:
                        pyautogui.keyDown('left')
                        time.sleep(0.3)
                        pyautogui.keyUp('left')
                    else:
                        self.keyboard.press(self.move_keys['left'])
                        time.sleep(0.3)
                        self.keyboard.release(self.move_keys['left'])
            
            # 爬繩子
            print("開始爬繩子向上")
            if self.use_pyautogui_keys:
                pyautogui.keyDown('up')
                time.sleep(1.5)  # 爬行時間
                pyautogui.keyUp('up')
            else:
                self.keyboard.press(self.rope_climb_key)
                time.sleep(1.5)
                self.keyboard.release(self.rope_climb_key)
            return True
        
        return False
    
    def detect_player_on_rope(self):
        """改進版：偵測玩家是否在繩子上（使用圖像模板）"""
        if self.player_on_rope_template is None:
            print("沒有玩家在繩子上的模板，使用位置估算")
            return self.detect_player_on_rope_fallback()
        
        # 截取螢幕
        screenshot = pyautogui.screenshot()
        screenshot_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # 使用多種預處理方式增強特徵
        original_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
        
        # 圖像增強 - 對比度提升
        enhanced_img = cv2.convertScaleAbs(screenshot_np, alpha=1.2, beta=10)
        enhanced_gray = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2GRAY)
        
        # 混合偵測策略
        detection_results = []
        
        # 定義較低閾值以增加召回率
        base_threshold = 0.55
        
        # 1. 先使用模板匹配 - 使用不同圖像和更寬的尺度範圍
        gray_images = [original_gray, enhanced_gray]
        for gray_idx, screenshot_gray in enumerate(gray_images):
            img_type = "原始" if gray_idx == 0 else "增強對比度"
            
            # 多尺度模板匹配
            best_confidence = 0
            best_location = None
            best_scale = 0
            
            # 擴展尺度範圍
            for scale in [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]:
                # 調整模板大小
                width = int(self.player_on_rope_template.shape[1] * scale)
                height = int(self.player_on_rope_template.shape[0] * scale)
                
                if width > screenshot_gray.shape[1] or height > screenshot_gray.shape[0]:
                    continue
                    
                resized_template = cv2.resize(self.player_on_rope_template, (width, height))
                
                # 模板匹配
                result = cv2.matchTemplate(screenshot_gray, resized_template, cv2.TM_CCOEFF_NORMED)
                _, max_confidence, _, max_loc = cv2.minMaxLoc(result)
                
                if max_confidence > best_confidence:
                    best_confidence = max_confidence
                    best_location = (max_loc[0] + width // 2, max_loc[1] + height // 2)
                    best_scale = scale
            
            if best_confidence >= base_threshold:
                detection_results.append({
                    'confidence': best_confidence,
                    'position': best_location,
                    'method': f"模板匹配 ({img_type})",
                    'scale': best_scale
                })
        
        # 2. 如果上述方法沒有足夠的信心度，嘗試位置關係判斷
        if not detection_results or max(r['confidence'] for r in detection_results) < 0.7:
            # 找到畫面中的繩子
            ropes = self.find_objects(self.rope_templates, threshold=0.7, debug=False)
            if ropes:
                player_pos = self.get_player_position()
                
                for rope in ropes:
                    rope_x, rope_y = rope['position']
                    rope_box = rope['box']
                    rope_width = rope_box[2]
                    
                    # 計算玩家與繩子中心的水平距離
                    dx = abs(player_pos[0] - rope_x)
                    
                    # 如果玩家在繩子上方，dx應該很小
                    if dx < rope_width/2 + 20:  # 加上一點容忍度
                        rope_confidence = 0.6  # 基於位置的置信度設定
                        detection_results.append({
                            'confidence': rope_confidence,
                            'position': (rope_x, player_pos[1]),  # 使用繩子的X座標和玩家的Y座標
                            'method': "繩子位置關係",
                            'rope_info': rope
                        })
        
        # 3. 選擇最佳結果
        if detection_results:
            # 按信心度排序
            detection_results.sort(key=lambda x: x['confidence'], reverse=True)
            best_result = detection_results[0]
            
            print(f"偵測到玩家在繩子上！方法: {best_result['method']}, 信心度: {best_result['confidence']:.2f}")
            
            # 保存debug圖像
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            debug_image = screenshot_np.copy()
            x, y = best_result['position']
            
            if 'scale' in best_result:  # 從模板匹配來的結果
                scale = best_result['scale']
                w = int(self.player_on_rope_template.shape[1] * scale)
                h = int(self.player_on_rope_template.shape[0] * scale)
                cv2.rectangle(debug_image, (x-w//2, y-h//2), (x+w//2, y+h//2), (0, 255, 255), 3)
            else:  # 從位置關係判斷來的結果
                cv2.circle(debug_image, (int(x), int(y)), 30, (0, 255, 255), 3)
            
            # 顯示所有偵測結果
            y_offset = 30
            for idx, result in enumerate(detection_results):
                confidence = result['confidence']
                method = result['method']
                text = f"{idx+1}. {method}: {confidence:.2f}"
                cv2.putText(debug_image, text, (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                y_offset += 25
            
            screens_dir = 'screens'
            if not os.path.exists(screens_dir):
                os.makedirs(screens_dir)
            debug_path = os.path.join(screens_dir, f"player_on_rope_{timestamp}.png")
            cv2.imwrite(debug_path, debug_image)
            print(f"偵測結果已保存: {debug_path}")
            
            return True, {'name': 'player_on_rope', 'confidence': best_result['confidence'], 'position': best_result['position']}
        else:
            print(f"玩家不在繩子上 (最高信心度: {max([r['confidence'] for r in detection_results] or [0]):.2f})")
            return False, None
    
    def detect_player_on_rope_fallback(self):
        """備用方法：使用位置估算偵測玩家是否在繩子上"""
        player_x, player_y = self.get_player_position()
        
        # 檢查玩家位置附近是否有繩子
        ropes = self.find_objects(self.rope_templates, threshold=0.7)
        
        for rope in ropes:
            rope_x, rope_y = rope['position']
            rope_box = rope['box']
            
            # 檢查玩家是否在繩子的範圍內
            rope_left = rope_box[0]
            rope_right = rope_box[0] + rope_box[2]
            rope_top = rope_box[1]
            rope_bottom = rope_box[1] + rope_box[3]
            
            # 如果玩家的 x 座標在繩子範圍內，且 y 座標也在繩子範圍內
            if (rope_left - 20 <= player_x <= rope_right + 20 and 
                rope_top - 20 <= player_y <= rope_bottom + 20):
                print(f"偵測到玩家在繩子上: {rope['name']}")
                return True, rope
        
        return False, None

    def climb_down_rope(self, method='down'):
        """下繩子到平台 - 支援三種方法"""
        print(f"開始下繩子（方法: {method}）...")
        if method == 'down':
            # 方法1: 按住下鍵（推薦，兼容性最好）
            print("使用按住下鍵的方法下繩子")
            if self.use_pyautogui_keys:
                pyautogui.keyDown('down')
                time.sleep(2.0)  # 持續下降2秒
                pyautogui.keyUp('down')
            else:
                self.keyboard.press(self.move_keys['down'])
                time.sleep(2.0)
                self.keyboard.release(self.move_keys['down'])
                
        elif method == 'left_jump':
            # 方法2: 向左跳（可能無效，因為遊戲可能不支援同時按鍵）
            print("使用向左跳的方法下繩子（可能無效）")
            if self.use_pyautogui_keys:
                pyautogui.keyDown('left')
                pyautogui.press('space')
                time.sleep(0.5)
                pyautogui.keyUp('left')
            else:
                self.keyboard.press(self.move_keys['left'])
                self.keyboard.press(self.jump_key)
                time.sleep(0.2)
                self.keyboard.release(self.jump_key)
                time.sleep(0.3)
                self.keyboard.release(self.move_keys['left'])
                
        elif method == 'right_jump':
            # 方法3: 向右跳（可能無效，因為遊戲可能不支援同時按鍵）
            print("使用向右跳的方法下繩子（可能無效）")
            if self.use_pyautogui_keys:
                pyautogui.keyDown('right')
                pyautogui.press('space')
                time.sleep(0.5)
                pyautogui.keyUp('right')
            else:
                self.keyboard.press(self.move_keys['right'])
                self.keyboard.press(self.jump_key)
                time.sleep(0.2)
                self.keyboard.release(self.jump_key)
                time.sleep(0.3)
                self.keyboard.release(self.move_keys['right'])
        
        print("下繩子完成")
        time.sleep(0.5)  # 等待穩定
    
    def simple_climb_down_rope(self):
        """簡化的下繩子方法 - 只使用按住下鍵"""
        print("使用簡化下繩子方法（僅按住下鍵）...")
        return self.improved_position_test(
            lambda: self.climb_down_rope('down'),
            "按住下鍵下繩"
        )
    
    def smart_climb_down_rope(self):
        """智能下繩子 - 嘗試不同方法，使用截圖差異判斷"""
        print("智能下繩子 - 嘗試多種方法...")
        
        # 嘗試方法1: 按住下鍵
        print("測試方法1: 按住下鍵")
        success = self.improved_position_test(
            lambda: self.climb_down_rope('down'),
            "按住下鍵下繩"
        )
        if success:
            print("✅ 按住下鍵成功下繩")
            return True
        
        # 檢查遊戲是否支援同時按兩鍵
        print("\n⚠️  注意：部分楓之谷版本可能不支援同時按方向鍵+跳躍鍵")
        print("如果左跳/右跳無效，建議只使用按住下鍵的方式")
        
        print("測試方法2: 向左跳")
        success = self.improved_position_test(
            lambda: self.climb_down_rope('left_jump'),
            "向左跳下繩"
        )
        if success:
            print("✅ 向左跳成功下繩")
            return True
        
        print("測試方法3: 向右跳")
        success = self.improved_position_test(
            lambda: self.climb_down_rope('right_jump'),
            "向右跳下繩"
        )
        if success:
            print("✅ 向右跳成功下繩")
            return True
        
        print("❌ 所有下繩方法都失敗")
        print("💡 建議：如果遊戲不支援同時按鍵，請只使用按住下鍵的方式")
        return False
    
    def check_same_platform(self, monster_pos, tolerance=50):
        """檢查怪物是否與玩家在同一平台"""
        player_x, player_y = self.get_player_position()
        monster_x, monster_y = monster_pos
        
        # 檢查 y 座標差異（垂直距離）
        vertical_distance = abs(player_y - monster_y)
        
        # 如果垂直距離小於容忍值，認為在同一平台
        return vertical_distance <= tolerance
    
    def wait_for_platform_clear(self, max_wait=10):
        """等待當前平台的怪物清空"""
        print("等待平台怪物清空...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            monsters = self.find_objects(self.monster_templates, threshold=0.7)
            
            # 檢查是否還有怪物在同一平台
            platform_monsters = []
            for monster in monsters:
                if self.check_same_platform(monster['position']):
                    platform_monsters.append(monster)
            
            if not platform_monsters:
                print("平台已清空")
                return True
            
            print(f"平台還有 {len(platform_monsters)} 隻怪物")
            time.sleep(1)
        
        print("等待超時，強制繼續")
        return False

    def auto_training_loop(self):
        """主要的自動練功循環"""
        print("開始自動練功...")
        print("按 Ctrl+C 可以停止")
        
        try:
            while True:
                # 0. 首先檢查是否在繩子上
                on_rope, rope_info = self.detect_player_on_rope()
                if on_rope:
                    print("偵測到玩家在繩子上")
                    
                    # 檢查下方是否有怪物
                    monsters = self.find_objects(self.monster_templates, threshold=0.7)
                    monsters_below = []
                    player_x, player_y = self.get_player_position()
                    
                    for monster in monsters:
                        mx, my = monster['position']
                        if my > player_y + 50:  # 怪物在下方
                            monsters_below.append(monster)
                    
                    if monsters_below:
                        print(f"發現下方有 {len(monsters_below)} 隻怪物，下繩子攻擊")
                        success = False
                        if self.climb_down_strategy == 'simple':
                            success = self.simple_climb_down_rope()
                        else:
                            success = self.smart_climb_down_rope()
                        
                        if success:
                            print("成功下繩子，等待攻擊")
                            time.sleep(1)
                        continue
                    else:
                        print("下方沒有怪物，繼續爬繩子尋找")
                        # 繼續向上爬
                        if self.use_pyautogui_keys:
                            pyautogui.press('up')
                        else:
                            self.keyboard.press(self.rope_climb_key)
                            time.sleep(0.5)
                            self.keyboard.release(self.rope_climb_key)
                        time.sleep(1)
                        continue
                
                # 偵測所有物件
                monsters = self.find_objects(self.monster_templates, threshold=0.7)
                ropes = self.find_objects(self.rope_templates, threshold=self.rope_threshold)
                platforms = self.find_objects(self.platform_templates, threshold=self.platform_threshold)
                
                print(f"偵測到: {len(monsters)} 怪物, {len(ropes)} 繩子, {len(platforms)} 平台")
                
                # 1. 優先攻擊同一平台的怪物
                target_monster = self.select_target_monster(monsters)
                
                if target_monster:
                    target_pos = target_monster['position']
                    player_pos = self.get_player_position()
                    distance = ((target_pos[0] - player_pos[0])**2 + (target_pos[1] - player_pos[1])**2)**0.5
                    
                    print(f"目標怪物: {target_monster['name']} 距離: {distance:.1f}")
                    
                    # 檢查是否在同一平台
                    if not self.check_same_platform(target_pos):
                        print("怪物不在同一平台，需要移動到相同平台")
                        # 如果怪物在上方，找繩子爬上去
                        if target_pos[1] < player_pos[1] - 50 and ropes:
                            print("怪物在上方，爬繩子")
                            if self.handle_rope(ropes):
                                time.sleep(2)
                                continue
                        # 如果怪物在下方，嘗試下跳
                        elif target_pos[1] > player_pos[1] + 50:
                            print("怪物在下方，下跳")
                            self.move_to_target(target_pos)
                            time.sleep(1)
                            continue
                    
                    if distance <= self.attack_range:
                        # 在攻擊範圍內且同一平台，開始攻擊
                        print("開始攻擊同平台怪物")
                        self.attack_target(target_monster)
                        
                        # 攻擊後等待平台清空
                        if target_monster.get('is_cluster', False):
                            print("群組攻擊完成，等待平台清空...")
                            self.wait_for_platform_clear()
                    else:
                        # 移動到怪物位置（同一平台）
                        self.move_to_target(target_pos)
                        time.sleep(0.5)
                        continue
                
                # 2. 沒有怪物時，檢查是否需要爬繩子
                elif ropes:
                    if self.handle_rope(ropes):
                        time.sleep(2)  # 爬繩後等待
                        continue
                
                # 3. 檢查平台下方怪物
                elif platforms:
                    platform_monster = self.check_platform_monsters(monsters, platforms)
                    if platform_monster:
                        print("下跳攻擊平台下方怪物")
                        self.move_to_target(platform_monster['position'])
                        time.sleep(1)
                        continue
                
                # 4. 沒有任何目標，隨機移動探索
                else:
                    self.add_debug_info("探索模式", "隨機移動尋找目標")
                    import random
                    direction = random.choice(['left', 'right'])
                    
                    if self.use_pyautogui_keys:
                        pyautogui.keyDown(direction)
                        time.sleep(random.uniform(1, 2))
                        pyautogui.keyUp(direction)
                    else:
                        self.keyboard.press(self.move_keys[direction])
                        time.sleep(random.uniform(1, 2))
                        self.keyboard.release(self.move_keys[direction])
                
                time.sleep(0.2)  # 減少主循環間隔，提高反應速度
                
        except KeyboardInterrupt:
            print("\n自動練功已停止")

    def test_keyboard_controls(self):
        """測試鍵盤控制是否正常工作"""
        print("開始測試鍵盤控制...")
        print("請切換到遊戲視窗")
        print("倒數計時：")
        for i in range(5, 0, -1):
            print(f"  {i} 秒...")
            time.sleep(1)
        print("開始測試！")
        time.sleep(0.5)
        
        # 測試攻擊鍵
        print("測試攻擊鍵 'x'...")
        self.keyboard.press('x')
        time.sleep(0.1)
        self.keyboard.release('x')
        time.sleep(1)
        
        # 測試方向鍵
        directions = ['left', 'right', 'up', 'down']
        for direction in directions:
            print(f"測試 {direction} 方向鍵...")
            key = self.move_keys[direction]
            self.keyboard.press(key)
            time.sleep(0.5)  # 持續按住0.5秒
            self.keyboard.release(key)
            time.sleep(0.5)
        
        # 測試跳躍
        print("測試跳躍鍵...")
        self.keyboard.press(self.jump_key)
        time.sleep(0.2)
        self.keyboard.release(self.jump_key)
        time.sleep(1)
        
        print("鍵盤測試完成")
    
    def alternative_move_to_target(self, target_pos):
        """使用 pyautogui 的替代移動方法"""
        player_x, player_y = self.get_player_position()
        target_x, target_y = target_pos
        
        dx = target_x - player_x
        dy = target_y - player_y
        
        # 使用 pyautogui 發送按鍵（有時候比 pynput 更有效）
        if abs(dx) > 30:
            if dx > 0:
                print("向右移動 (pyautogui)")
                pyautogui.keyDown('right')
                time.sleep(min(abs(dx) / 200, 1.0))
                pyautogui.keyUp('right')
            else:
                print("向左移動 (pyautogui)")
                pyautogui.keyDown('left')
                time.sleep(min(abs(dx) / 200, 1.0))
                pyautogui.keyUp('left')
        
        # 垂直移動
        if dy < -50:
            print("跳躍 (pyautogui)")
            pyautogui.press('space')
        elif dy > 100:
            print("下跳 (pyautogui)")
            pyautogui.keyDown('down')
            pyautogui.press('space')
            pyautogui.keyUp('down')

    def take_debug_screenshot(self, description="manual"):
        """手動拍照用於 debug"""
        screens_dir = 'screens'
        if not os.path.exists(screens_dir):
            os.makedirs(screens_dir)
        
        screenshot = pyautogui.screenshot()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(screens_dir, f"{description}_{timestamp}.png")
        screenshot.save(screenshot_path)
        print(f"截圖已保存: {screenshot_path}")
        return screenshot_path

    def find_monster_clusters(self, monsters, cluster_radius=100):
        """找到怪物密集區域"""
        if not monsters:
            return []
        
        clusters = []
        
        # 為每個怪物計算周圍的怪物密度
        for i, monster in enumerate(monsters):
            x, y = monster['position']
            nearby_monsters = []
            
            for j, other_monster in enumerate(monsters):
                if i != j:  # 不包括自己
                    ox, oy = other_monster['position']
                    distance = ((x - ox)**2 + (y - oy)**2)**0.5
                    
                    if distance <= cluster_radius:
                        nearby_monsters.append(other_monster)
            
            # 包括自己
            cluster_monsters = [monster] + nearby_monsters
            
            # 計算群組的中心點和總優先級
            center_x = sum(m['position'][0] for m in cluster_monsters) / len(cluster_monsters)
            center_y = sum(m['position'][1] for m in cluster_monsters) / len(cluster_monsters)
            total_priority = sum(m.get('priority', 5) for m in cluster_monsters)
            
            cluster_info = {
                'center': (center_x, center_y),
                'monster_count': len(cluster_monsters),
                'monsters': cluster_monsters,
                'total_priority': total_priority,
                'density_score': len(cluster_monsters) * total_priority  # 密度分數
            }
            
            clusters.append(cluster_info)
        
        # 去除重複的群組（基於中心點距離）
        unique_clusters = []
        for cluster in clusters:
            is_duplicate = False
            for existing in unique_clusters:
                cx, cy = cluster['center']
                ex, ey = existing['center']
                distance = ((cx - ex)**2 + (cy - ey)**2)**0.5
                
                if distance < cluster_radius / 2:  # 如果群組中心太近，認為是重複
                    # 保留怪物數量更多的群組
                    if cluster['monster_count'] > existing['monster_count']:
                        unique_clusters.remove(existing)
                        unique_clusters.append(cluster)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_clusters.append(cluster)
        
        # 按密度分數排序（怪物越多、優先級越高的群組排在前面）
        unique_clusters.sort(key=lambda x: x['density_score'], reverse=True)
        
        return unique_clusters
    
    def select_best_target_area(self, monsters):
        """選擇最佳攻擊區域"""
        if not monsters:
            return None
        
        # 找到怪物群組
        clusters = self.find_monster_clusters(monsters)
        
        if clusters:
            best_cluster = clusters[0]  # 密度分數最高的群組
            print(f"選中最佳區域: {best_cluster['monster_count']} 隻怪物，密度分數: {best_cluster['density_score']}")
            
            # 返回群組中心位置作為目標
            return {
                'position': best_cluster['center'],
                'monster_count': best_cluster['monster_count'],
                'cluster_info': best_cluster
            }
        else:
            # 如果沒有群組，選擇單一怪物
            best_monster = max(monsters, key=lambda m: m.get('priority', 5))
            return {
                'position': best_monster['position'],
                'monster_count': 1,
                'cluster_info': None
            }
    
    def test_rope_detection_with_threshold(self, threshold=0.7):
        """改進版：測試不同閾值下的繩子偵測效果，並診斷問題"""
        if self.player_on_rope_template is None:
            print("沒有 role_on_rope.png 模板")
            return
        
        print(f"測試閾值: {threshold}")
        print("=" * 60)
        
        # 截取螢幕
        screenshot = pyautogui.screenshot()
        screenshot_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # 準備不同處理的圖像
        original_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
        
        # 增強對比度
        enhanced_img = cv2.convertScaleAbs(screenshot_np, alpha=1.2, beta=10)
        enhanced_gray = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2GRAY)
        
        # 嘗試不同圖像處理方法
        img_types = [
            {"name": "原始圖像", "img": original_gray},
            {"name": "增強對比度", "img": enhanced_gray}
        ]
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screens_dir = 'screens'
        if not os.path.exists(screens_dir):
            os.makedirs(screens_dir)
        
        # 準備診斷圖像
        debug_image = screenshot_np.copy()
        
        all_matches = []
        best_match_per_method = []
        
        # 使用不同的圖像處理方法
        for img_type in img_types:
            type_name = img_type["name"]
            screenshot_gray = img_type["img"]
            
            print(f"\n測試 {type_name}:")
            
            # 最佳匹配（此方法）
            best_match = None
            best_confidence = 0
            
            # 多尺度模板匹配
            for scale in [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]:
                width = int(self.player_on_rope_template.shape[1] * scale)
                height = int(self.player_on_rope_template.shape[0] * scale)
                
                if width > screenshot_gray.shape[1] or height > screenshot_gray.shape[0]:
                    continue
                    
                resized_template = cv2.resize(self.player_on_rope_template, (width, height))
                result = cv2.matchTemplate(screenshot_gray, resized_template, cv2.TM_CCOEFF_NORMED)
                
                # 找到所有匹配位置
                locations = np.where(result >= threshold)
                
                matches_found = 0
                for pt in zip(*locations[::-1]):
                    x, y = pt
                    confidence = result[y, x]
                    
                    match = {
                        'position': (x + width // 2, y + height // 2),
                        'confidence': confidence,
                        'scale': scale,
                        'box': (x, y, width, height),
                        'method': type_name
                    }
                    
                    all_matches.append(match)
                    matches_found += 1
                    
                    # 記錄最佳匹配
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = match
                    
                print(f"  尺度 {scale:.1f}x: 找到 {matches_found} 個匹配")
                
                # 如果沒有匹配，找出最高信心度的位置（即使低於閾值）
                if matches_found == 0:
                    _, max_confidence, _, max_loc = cv2.minMaxLoc(result)
                    print(f"  - 最高信心度: {max_confidence:.3f} (低於閾值 {threshold})")
            
            if best_match:
                best_match_per_method.append(best_match)
                print(f"  ✅ 最佳匹配: 信心度 {best_confidence:.3f}, 尺度 {best_match['scale']:.1f}x")
            else:
                print(f"  ❌ 沒有找到匹配 (閾值 {threshold})")
        
        # 檢查繩子位置
        print("\n檢查繩子位置關係:")
        ropes = self.find_objects(self.rope_templates, threshold=0.7, debug=False)
        if ropes:
            print(f"  找到 {len(ropes)} 條繩子")
            player_pos = self.get_player_position()
            
            for i, rope in enumerate(ropes):
                rope_x, rope_y = rope['position']
                rope_box = rope['box']
                rope_width = rope_box[2]
                
                # 計算玩家與繩子中心的水平距離
                dx = abs(player_pos[0] - rope_x)
                
                print(f"  繩子 {i+1}: 位置 {rope['position']}, 玩家水平距離: {dx:.1f}px")
                
                # 標記繩子位置
                x, y, w, h = rope_box
                cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 165, 255), 2)
                cv2.putText(debug_image, f"Rope {i+1}", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
                
                # 如果玩家在繩子上方，dx應該很小
                if dx < rope_width/2 + 20:  # 加上一點容忍度
                    print(f"  ✅ 玩家可能在繩子 {i+1} 上! (水平距離: {dx:.1f}px)")
                    
                    # 添加到匹配結果
                    all_matches.append({
                        'position': (rope_x, player_pos[1]),
                        'confidence': 0.6,  # 基於位置的置信度
                        'method': "繩子位置關係",
                        'rope_info': rope
                    })
                    
                    # 標記玩家與繩子的關係
                    cv2.line(debug_image, 
                            (int(player_pos[0]), int(player_pos[1])),
                            (int(rope_x), int(player_pos[1])),
                            (0, 255, 0), 2)
        else:
            print("  ❌ 沒有找到繩子")
        
        # 繪製所有最佳匹配
        for idx, match in enumerate(best_match_per_method):
            x, y = match['position']
            w, h = match['box'][2], match['box'][3]
            
            # 使用不同顏色區分不同方法
            color = (0, 255, 255) if idx == 0 else (255, 0, 255)
            
            cv2.rectangle(debug_image, (x, y), (x+w, y+h), color, 2)
            cv2.putText(debug_image, f"{match['method']}: {match['confidence']:.2f}", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 標記玩家位置 (估算)
        player_pos = self.get_player_position()
        cv2.circle(debug_image, (int(player_pos[0]), int(player_pos[1])), 20, (255, 255, 255), 2)
        cv2.putText(debug_image, "Estimated Player", (int(player_pos[0])+25, int(player_pos[1])),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 保存診斷圖像
        debug_path = os.path.join(screens_dir, f"rope_detection_debug_{timestamp}.png")
        cv2.imwrite(debug_path, debug_image)
        
        # 排序所有匹配
        all_matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        print("\n診斷摘要:")
        print(f"找到總共 {len(all_matches)} 個匹配（閾值 >= {threshold}）")
        for i, match in enumerate(all_matches[:5]):  # 只顯示前5個
            method = match.get('method', '未知方法')
            if 'scale' in match:
                print(f"  {i+1}. 方法: {method}, 位置: {match['position']}, 信心度: {match['confidence']:.3f}, 尺度: {match['scale']}")
            else:
                print(f"  {i+1}. 方法: {method}, 位置: {match['position']}, 信心度: {match['confidence']:.3f}")
        
        # 診斷建議
        print("\n診斷結果:")
        if all_matches:
            best_match = all_matches[0]
            print(f"✅ 最佳偵測方法: {best_match.get('method', '模板匹配')}")
            print(f"   信心度: {best_match['confidence']:.3f}")
            
            if best_match['confidence'] < 0.6:
                print("⚠️  信心度較低，可能需要:")
                print("   1. 更新角色在繩子上的模板")
                print("   2. 嘗試使用更低的閾值 (0.5-0.6)")
                print("   3. 組合使用模板匹配和位置關係")
            
            if 'method' in best_match and best_match['method'] == "繩子位置關係":
                print("💡 建議: 位置關係判斷效果良好，考慮優先使用此方法")
        else:
            print("❌ 偵測失敗，可能原因:")
            print("   1. 角色不在繩子上")
            print("   2. 模板與實際情況不匹配")
            print("   3. 閾值設定過高")
            print("\n💡 建議:")
            print("   - 使用閾值 0.5-0.6 重試")
            print("   - 更新角色在繩子上的模板圖像")
            print("   - 結合繩子位置關係和顏色偵測")
        
        print(f"\n診斷圖像已保存: {debug_path}")
        print("=" * 60)
        
        return all_matches

    def force_test_movement(self):
        """強制測試移動功能（用於驗證按鍵是否有效）"""
        print("=== 強制移動測試開始 ===")
        
        movements = [
            ('左', 'left', 1.0),
            ('右', 'right', 1.0),
            ('跳躍', 'space', 0.5),
            ('攻擊', 'x', 0.3)
        ]
        
        for name, key, duration in movements:
            print(f"測試 {name} ({key})...")
            
            if self.use_pyautogui_keys:
                if key == 'space':
                    pyautogui.press('space')
                elif key in ['x']:
                    pyautogui.press(key)
                else:
                    pyautogui.keyDown(key)
                    time.sleep(duration)
                    pyautogui.keyUp(key)
            else:
                if key == 'space':
                    self.keyboard.press(self.jump_key)
                    time.sleep(0.2)
                    self.keyboard.release(self.jump_key)
                elif key in ['x']:
                    self.keyboard.press(key)
                    time.sleep(0.1)
                    self.keyboard.release(key)
                else:
                    move_key = self.move_keys.get(key, key)
                    self.keyboard.press(move_key)
                    time.sleep(duration)
                    self.keyboard.release(move_key)
            
            time.sleep(1)  # 等待觀察效果
        
        print("=== 強制移動測試完成 ===")
    
    def test_climb_down_methods(self):
        """測試所有下繩子方法（使用截圖差異判斷）"""
        print("測試下繩子方法...")
        print("請確保您的角色在繩子上")
        
        # 讓用戶選擇按鍵方法
        print("\n選擇按鍵方法:")
        print("1. 使用 pyautogui")
        print("2. 使用 pynput")
        key_choice = input("請選擇 (1/2): ").strip()
        
        original_method = self.use_pyautogui_keys
        if key_choice == '1':
            self.use_pyautogui_keys = True
            print("✅ 使用 pyautogui 方法")
        elif key_choice == '2':
            self.use_pyautogui_keys = False
            print("✅ 使用 pynput 方法")
        else:
            print("使用當前設定")
        
        print("\n⚠️  重要提醒：")
        print("- 左跳/右跳下繩子若遊戲不支援同時按兩鍵，可能無效")
        print("- 大部分楓之谷版本建議只使用按住下鍵的方式")
        print("- 測試結果將以螢幕畫面變化程度來判斷")
        
        print("\n請切換到遊戲視窗並確保角色在繩子上")
        print("倒數計時：")
        for i in range(5, 0, -1):
            print(f"  {i} 秒...")
            time.sleep(1)
        print("開始測試！")
        time.sleep(0.5)
        
        methods = [
            ('down', '按住下鍵（推薦）'),
            ('left_jump', '向左跳（可能無效）'),
            ('right_jump', '向右跳（可能無效）')
        ]
        
        successful_methods = []
        
        for method, description in methods:
            print(f"\n{'='*50}")
            print(f"測試方法: {description}")
            print(f"按鍵方法: {'pyautogui' if self.use_pyautogui_keys else 'pynput'}")
            print("請確保遊戲視窗在前景且角色在繩子上")
            input(f"準備好後按 Enter 開始測試...")
            
            print("3秒後開始執行...")
            for i in range(3, 0, -1):
                print(f"  {i}...")
                time.sleep(1)
            
            # 使用改進的位置測試方法
            success = self.improved_position_test(
                lambda m=method: self.climb_down_rope(m),
                f"{description}下繩"
            )
            
            if success:
                print(f"✅ {description} 方法有效")
                successful_methods.append(method)
            else:
                print(f"❌ {description} 方法無效或效果不明顯")
                if method in ['left_jump', 'right_jump']:
                    print("    提示：遊戲可能不支援同時按方向鍵+跳躍鍵")
            
            print("-" * 50)
            time.sleep(2)
        
        # 顯示測試總結
        print(f"\n{'='*50}")
        print("測試總結:")
        if successful_methods:
            print(f"✅ 有效的下繩方法: {', '.join(successful_methods)}")
            if 'down' in successful_methods:
                print("建議：優先使用按住下鍵方法（兼容性最好）")
        else:
            print("❌ 沒有檢測到有效的下繩方法")
            print("可能原因：")
            print("1. 角色不在繩子上")
            print("2. 遊戲按鍵設定不同")
            print("3. 需要手動調整按鍵映射")
        
        # 恢復原設定
        self.use_pyautogui_keys = original_method
        print(f"\n設定已恢復: {'pyautogui' if self.use_pyautogui_keys else 'pynput'}")
        
        return successful_methods
    
    def simple_key_test(self):
        """簡單的按鍵測試"""
        print("簡單按鍵測試...")
        print("請切換到遊戲視窗")
        print("倒數計時：")
        for i in range(5, 0, -1):
            print(f"  {i} 秒...")
            time.sleep(1)
        print("開始測試！")
        time.sleep(0.5)
        
        # 測試 pyautogui 方法
        print("\n=== 測試 pyautogui 方法 ===")
        print("測試向右移動...")
        pyautogui.keyDown('right')
        time.sleep(1)
        pyautogui.keyUp('right')
        time.sleep(1)
        
        print("測試跳躍...")
        pyautogui.press('space')
        time.sleep(1)
        
        print("測試下鍵...")
        pyautogui.keyDown('down')
        time.sleep(1)
        pyautogui.keyUp('down')
        time.sleep(1)
        
        # 測試 pynput 方法
        print("\n=== 測試 pynput 方法 ===")
        print("測試向左移動...")
        self.keyboard.press(Key.left)
        time.sleep(1)
        self.keyboard.release(Key.left)
        time.sleep(1)
        
        print("測試跳躍...")
        self.keyboard.press(Key.space)
        time.sleep(0.2)
        self.keyboard.release(Key.space)
        time.sleep(1)
        
        print("測試下鍵...")
        self.keyboard.press(Key.down)
        time.sleep(1)
        self.keyboard.release(Key.down)
        
        print("按鍵測試完成！")

    def add_debug_info(self, action, details=""):
        """添加詳細的 debug 資訊"""
        timestamp = time.strftime("%H:%M:%S")
        player_pos = self.get_player_position()
        print(f"[{timestamp}] {action} - 玩家位置: {player_pos} {details}")
    
    def show_current_settings(self):
        """顯示當前的機器人設定"""
        print("=" * 50)
        print("當前設定:")
        print(f"  按鍵方法: {'pyautogui' if self.use_pyautogui_keys else 'pynput'}")
        print(f"  下繩子策略: {'簡化模式（僅按住下鍵）' if self.climb_down_strategy == 'simple' else '智能模式（嘗試多種方法）'}")
        print(f"  攻擊範圍: {self.attack_range} 像素")
        print(f"  安全距離: {self.safe_distance} 像素")
        print("=" * 50)
    
    def debug_climb_down_test(self):
        """偵錯版下繩子測試 - 提供詳細分析"""
        print("偵錯版下繩子測試")
        print("=" * 60)
        print("此測試將提供詳細的分析資訊，幫助診斷問題")
        
        # 先檢查當前是否在繩子上
        print("\n1. 檢查角色是否在繩子上...")
        on_rope, rope_info = self.detect_player_on_rope()
        if on_rope:
            print("  ✅ 偵測到角色在繩子上")
            if rope_info:
                print(f"     詳細資訊: {rope_info}")
        else:
            print("  ⚠️  未偵測到角色在繩子上")
            print("     這可能會影響測試結果")
        
        print("\n2. 選擇按鍵方法...")
        print("1. pyautogui (通常較穩定)")
        print("2. pynput (可能在某些系統上更準確)")
        key_choice = input("請選擇按鍵方法 (1/2): ").strip()
        
        original_method = self.use_pyautogui_keys
        if key_choice == '2':
            self.use_pyautogui_keys = False
            print("使用 pynput 方法")
        else:
            self.use_pyautogui_keys = True
            print("使用 pyautogui 方法")
        
        print("\n3. 開始詳細測試...")
        print("請切換到遊戲視窗並確保角色在繩子上")
        input("準備好後按 Enter 繼續...")
        
        print("倒數計時：")
        for i in range(5, 0, -1):
            print(f"  {i} 秒...")
            time.sleep(1)
        
        # 只測試按住下鍵方法，但提供極詳細的分析
        print("\n測試：按住下鍵方法")
        print("-" * 40)
        
        # 詳細記錄按鍵過程
        print("執行步驟:")
        print("  1. 截取動作前畫面")
        screenshot_before = pyautogui.screenshot()
        
        print("  2. 按下並持續按住下鍵")
        if self.use_pyautogui_keys:
            print("     pyautogui.keyDown('down')")
            pyautogui.keyDown('down')
        else:
            print("     keyboard.press(Key.down)")
            self.keyboard.press(self.move_keys['down'])
        
        print("  3. 持續 2 秒...")
        for i in range(20):  # 2秒，每0.1秒顯示一次
            print(f"     按住中... ({(i+1)*0.1:.1f}s)")
            time.sleep(0.1)
        
        print("  4. 釋放下鍵")
        if self.use_pyautogui_keys:
            print("     pyautogui.keyUp('down')")
            pyautogui.keyUp('down')
        else:
            print("     keyboard.release(Key.down)")
            self.keyboard.release(self.move_keys['down'])
        
        print("  5. 等待動作完成...")
        time.sleep(1)
        
        print("  6. 截取動作後畫面並分析")
        screenshot_after = pyautogui.screenshot()
        
        # 詳細分析
        img1 = cv2.cvtColor(np.array(screenshot_before), cv2.COLOR_RGB2BGR)
        img2 = cv2.cvtColor(np.array(screenshot_after), cv2.COLOR_RGB2BGR)
        
        diff = cv2.absdiff(img1, img2)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        # 區域分析
        height, width = gray_diff.shape
        center_y, center_x = height // 2, width // 2
        
        # 分析不同區域的變化
        regions = {
            '全畫面': gray_diff,
            '中央區域': gray_diff[center_y-100:center_y+100, center_x-100:center_x+100],
            '下半部': gray_diff[center_y:, :],
            '上半部': gray_diff[:center_y, :]
        }
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        print("\n分析結果:")
        for region_name, region in regions.items():
            if region.size > 0:
                change_pixels = cv2.countNonZero(region)
                total_pixels = region.shape[0] * region.shape[1]
                change_percentage = (change_pixels / total_pixels) * 100
                print(f"  {region_name}: {change_percentage:.3f}% 變化 ({change_pixels}/{total_pixels} 像素)")
        
        # 保存詳細的除錯圖像
        screens_dir = 'screens'
        if not os.path.exists(screens_dir):
            os.makedirs(screens_dir)
        
        before_path = os.path.join(screens_dir, f"debug_before_{timestamp}.png")
        after_path = os.path.join(screens_dir, f"debug_after_{timestamp}.png")
        diff_path = os.path.join(screens_dir, f"debug_diff_{timestamp}.png")
        
        screenshot_before.save(before_path)
        screenshot_after.save(after_path)
        cv2.imwrite(diff_path, diff)
        
        print(f"\n除錯圖像已保存:")
        print(f"  動作前: {before_path}")
        print(f"  動作後: {after_path}")
        print(f"  差異圖: {diff_path}")
        
        # 恢復原設定
        self.use_pyautogui_keys = original_method
        
        print("\n診斷建議:")
        total_change = (cv2.countNonZero(gray_diff) / gray_diff.size) * 100
        if total_change > 1.0:
            print("  ✅ 檢測到明顯的畫面變化，下繩子功能應該正常")
        elif total_change > 0.1:
            print("  ⚠️  檢測到輕微變化，可能:")
            print("     - 角色有移動但幅度較小")
            print("     - 背景變化不明顯")
            print("     - 需要調整檢測閾值")
        else:
            print("  ❌ 幾乎沒有檢測到變化，可能原因:")
            print("     - 角色不在繩子上")
            print("     - 按鍵沒有被正確執行")
            print("     - 遊戲視窗不在前景")
            print("     - 按鍵映射不正確")
        
        print("=" * 60)
    
    def debug_object_detection(self):
        """偵錯物件偵測功能"""
        print("物件偵測偵錯工具")
        print("=" * 60)
        
        # 顯示載入的模板
        print("1. 載入的模板摘要:")
        print(f"   怪物模板: {len(self.monster_templates)}")
        for monster in self.monster_templates:
            print(f"     - {monster['name']} (尺寸: {monster['template'].shape})")
        
        print(f"   繩子模板: {len(self.rope_templates)}")
        for rope in self.rope_templates:
            print(f"     - {rope['name']} (尺寸: {rope['template'].shape})")
        
        print(f"   平台模板: {len(self.platform_templates)}")
        for platform in self.platform_templates:
            print(f"     - {platform['name']} (尺寸: {platform['template'].shape})")
        
        print("\n2. 選擇偵測類型:")
        print("1. 怪物偵測")
        print("2. 繩子偵測")
        print("3. 平台偵測")
        print("4. 全部偵測")
        
        choice = input("請選擇 (1-4): ").strip()
        
        print("\n3. 設定偵測閾值:")
        try:
            threshold = float(input("請輸入閾值 (0.1-1.0，建議0.5-0.8): "))
            threshold = max(0.1, min(1.0, threshold))
        except ValueError:
            threshold = 0.7
            print("使用預設閾值: 0.7")
        
        print("\n請切換到遊戲視窗...")
        print("倒數計時：")
        for i in range(3, 0, -1):
            print(f"  {i} 秒...")
            time.sleep(1)
        
        print("\n4. 開始偵錯偵測...")
        
        if choice == '1':
            print("偵測怪物...")
            monsters = self.find_objects(self.monster_templates, threshold=threshold, debug=True)
            print(f"\n結果: 找到 {len(monsters)} 個怪物")
            for i, monster in enumerate(monsters):
                print(f"  {i+1}. {monster['name']} - 信心度: {monster['confidence']:.3f} - 位置: {monster['position']}")
        
        elif choice == '2':
            print("偵測繩子...")
            ropes = self.find_objects(self.rope_templates, threshold=threshold, debug=True)
            print(f"\n結果: 找到 {len(ropes)} 條繩子")
            for i, rope in enumerate(ropes):
                print(f"  {i+1}. {rope['name']} - 信心度: {rope['confidence']:.3f} - 位置: {rope['position']}")
        
        elif choice == '3':
            print("偵測平台...")
            platforms = self.find_objects(self.platform_templates, threshold=threshold, debug=True)
            print(f"\n結果: 找到 {len(platforms)} 個平台")
            for i, platform in enumerate(platforms):
                print(f"  {i+1}. {platform['name']} - 信心度: {platform['confidence']:.3f} - 位置: {platform['position']}")
        
        elif choice == '4':
            print("偵測所有物件...")
            
            print("偵測怪物...")
            monsters = self.find_objects(self.monster_templates, threshold=threshold, debug=True)
            
            print("\n偵測繩子...")
            ropes = self.find_objects(self.rope_templates, threshold=threshold, debug=True)
            
            print("\n偵測平台...")
            platforms = self.find_objects(self.platform_templates, threshold=threshold, debug=True)
            
            print(f"\n總結果:")
            print(f"  怪物: {len(monsters)} 個")
            print(f"  繩子: {len(ropes)} 條")
            print(f"  平台: {len(platforms)} 個")
            
            # 檢查是否有分類錯誤
            print(f"\n詳細分析:")
            all_objects = monsters + ropes + platforms
            
            # 按信心度排序
            all_objects.sort(key=lambda x: x['confidence'], reverse=True)
            
            print("前10個最高信心度的偵測結果:")
            for i, obj in enumerate(all_objects[:10]):
                obj_type = obj.get('type', 'unknown')
                print(f"  {i+1}. {obj['name']} ({obj_type}) - 信心度: {obj['confidence']:.3f}")
        
        print("\n5. 診斷建議:")
        if choice == '1' or choice == '4':
            if len(monsters) == 0:
                print("  ❌ 沒有偵測到怪物，可能原因:")
                print("     - 怪物模板與實際怪物外觀不匹配")
                print("     - 閾值設定太高")
                print("     - 怪物被其他物件遮擋")
                print("     - 螢幕中沒有怪物")
            elif len(monsters) > 50:
                print("  ⚠️  偵測到過多怪物，可能原因:")
                print("     - 閾值設定太低")
                print("     - 模板過於通用，匹配到非怪物物件")
                print("     - 需要更精確的怪物模板")
        
        print("=" * 60)
    
    def test_color_detection(self):
        """測試顏色偵測功能 - 實驗性功能"""
        print("顏色偵測測試（實驗性功能）")
        print("=" * 60)
        print("這個功能嘗試使用顏色偵測來識別怪物和物件")
        print("相比模板匹配，顏色偵測可能更穩定且不受外觀變化影響")
        
        print("\n請切換到遊戲視窗...")
        print("倒數計時：")
        for i in range(3, 0, -1):
            print(f"  {i} 秒...")
            time.sleep(1)
        
        # 截取螢幕
        screenshot = pyautogui.screenshot()
        screenshot_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        screenshot_hsv = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2HSV)
        
        print("分析螢幕顏色分布...")
        
        # 定義一些常見的遊戲物件顏色範圍（HSV）
        color_ranges = {
            '怪物紅色': {
                'lower': np.array([0, 100, 100]),    # 紅色下限
                'upper': np.array([10, 255, 255]),   # 紅色上限
                'color': (0, 0, 255)  # BGR中的紅色
            },
            '怪物橙色': {
                'lower': np.array([10, 100, 100]),   # 橙色下限
                'upper': np.array([25, 255, 255]),   # 橙色上限
                'color': (0, 165, 255)  # BGR中的橙色
            },
            '繩子棕色': {
                'lower': np.array([8, 50, 50]),      # 棕色下限
                'upper': np.array([20, 200, 200]),   # 棕色上限
                'color': (42, 42, 165)  # BGR中的棕色
            },
            'HP條綠色': {
                'lower': np.array([40, 50, 50]),     # 綠色下限
                'upper': np.array([80, 255, 255]),   # 綠色上限
                'color': (0, 255, 0)  # BGR中的綠色
            },
            '文字白色': {
                'lower': np.array([0, 0, 200]),      # 白色下限
                'upper': np.array([180, 30, 255]),   # 白色上限
                'color': (255, 255, 255)  # BGR中的白色
            }
        }
        
        # 創建結果圖像
        result_image = screenshot_np.copy()
        
        # 保存結果
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screens_dir = 'screens'
        if not os.path.exists(screens_dir):
            os.makedirs(screens_dir)
        
        detected_objects = {}
        
        for color_name, color_info in color_ranges.items():
            print(f"\n檢測 {color_name}...")
            
            # 創建顏色遮罩
            mask = cv2.inRange(screenshot_hsv, color_info['lower'], color_info['upper'])
            
            # 形態學操作來清理遮罩
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # 尋找輪廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 過濾小的輪廓
            significant_contours = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100:  # 最小面積閾值
                    significant_contours.append(contour)
            
            detected_objects[color_name] = len(significant_contours)
            
            # 在結果圖像上標記偵測到的區域
            for contour in significant_contours:
                # 獲取邊界框
                x, y, w, h = cv2.boundingRect(contour)
                center_x, center_y = x + w//2, y + h//2
                
                # 畫邊界框
                cv2.rectangle(result_image, (x, y), (x+w, y+h), color_info['color'], 2)
                
                # 添加標籤
                cv2.putText(result_image, f"{color_name}", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_info['color'], 1)
            
            print(f"  找到 {len(significant_contours)} 個 {color_name} 區域")
            
            # 保存單獨的遮罩圖像
            mask_path = os.path.join(screens_dir, f"color_mask_{color_name}_{timestamp}.png")
            cv2.imwrite(mask_path, mask)
        
        # 保存標記結果
        result_path = os.path.join(screens_dir, f"color_detection_result_{timestamp}.png")
        cv2.imwrite(result_path, result_image)
        
        print(f"\n顏色偵測總結:")
        for color_name, count in detected_objects.items():
            print(f"  {color_name}: {count} 個區域")
        
        print(f"\n圖像已保存:")
        print(f"  標記結果: {result_path}")
        print(f"  各顏色遮罩: screens/color_mask_*_{timestamp}.png")
        
        # 分析結果並提供建議
        print(f"\n分析與建議:")
        
        if detected_objects.get('HP條綠色', 0) > 0:
            print("  ✅ 偵測到綠色HP條，可能有怪物存在")
        
        if detected_objects.get('怪物紅色', 0) + detected_objects.get('怪物橙色', 0) > 0:
            print("  ✅ 偵測到紅/橙色區域，可能是怪物本體")
        
        if detected_objects.get('繩子棕色', 0) > 0:
            print("  ✅ 偵測到棕色區域，可能是繩子")
        
        print("\n顏色偵測的優勢:")
        print("  1. 不受怪物外觀變化影響")
        print("  2. 可以偵測HP條來確認怪物")
        print("  3. 處理速度快")
        print("  4. 對光照變化相對穩定")
        
        print("\n後續改進方向:")
        print("  1. 根據實際遊戲調整顏色範圍")
        print("  2. 結合位置和大小過濾")
        print("  3. 使用多個顏色特徵組合判斷")
        print("  4. 可以替代或輔助模板匹配")
        
        print("=" * 60)

# 使用範例
if __name__ == "__main__":
    bot = AutoTrainingBot()
    
    print("楓之谷自動練功腳本")
    print("=" * 50)
    print("選擇模式:")
    print("1. 測試鍵盤控制")
    print("2. 簡單按鍵測試（對比 pyautogui vs pynput）")
    print("3. 測試物件偵測（基本）")
    print("4. 偵錯物件偵測（詳細分析）")
    print("5. 測試顏色偵測（實驗性功能）")
    print("6. 測試繩子偵測 (角色在繩子上)")
    print("7. 測試下繩子方法（完整測試）")
    print("8. 詳細測試繩子偵測（調整閾值與診斷問題）")
    print("9. 配置下繩子策略")
    print("10. 偵錯下繩子問題（詳細分析）")
    print("11. 開始自動練功")
    print("=" * 50)
    print("角色在繩子上偵測問題提示：使用選項6和選項8進行診斷")
    print("=" * 50)
    
    choice = input("請選擇 (1-11): ").strip()
    
    # 不同選項需要不同的準備說明
    if choice in ['1', '2', '7', '10']:
        print("注意：此選項會控制角色移動，請確保切換到遊戲視窗！")
    elif choice == '11':
        print("注意：即將開始自動練功，請確保角色在安全位置！")
    else:
        print("準備執行測試...")
    
    # 只有特定選項才需要額外等待（其他選項已有內建倒數）
    if choice in ['3', '4', '5', '6', '8', '11']:
        print("請切換到遊戲視窗...")
        print("倒數計時：")
        for i in range(3, 0, -1):
            print(f"  {i} 秒...")
            time.sleep(1)
        print("開始執行！")
    
    if choice == '1':
        bot.test_keyboard_controls()
        
    elif choice == '2':
        bot.simple_key_test()
        
    elif choice == '3':
        print("測試物件偵測（基本）...")
        monsters = bot.find_objects(bot.monster_templates, debug=True)
        ropes = bot.find_objects(bot.rope_templates, debug=True)
        platforms = bot.find_objects(bot.platform_templates, debug=True)
        
        print(f"\n總結: 偵測到 {len(monsters)} 怪物, {len(ropes)} 繩子, {len(platforms)} 平台")
        
        if monsters:
            print("怪物列表:")
            for i, monster in enumerate(monsters):
                print(f"  {i+1}. {monster['name']} - 信心度: {monster['confidence']:.3f} - 位置: {monster['position']}")
            
            target = bot.select_target_monster(monsters)
            if target:
                print(f"\n選中目標: {target['name']} 優先級: {target.get('priority', 5)}")
        
        if ropes:
            print("繩子列表:")
            for i, rope in enumerate(ropes):
                print(f"  {i+1}. {rope['name']} - 信心度: {rope['confidence']:.3f} - 位置: {rope['position']}")
    
    elif choice == '4':
        print("偵錯物件偵測（詳細分析）...")
        bot.debug_object_detection()
    
    elif choice == '5':
        print("測試顏色偵測（實驗性功能）...")
        bot.test_color_detection()

    elif choice == '6':
        print("測試繩子偵測...")
        print("=" * 50)
        
        # 測試玩家在繩子上的偵測
        on_rope, rope_info = bot.detect_player_on_rope()
        if on_rope:
            print(f"✅ 玩家在繩子上!")
            if rope_info:
                print(f"   詳細資訊: {rope_info}")
        else:
            print("❌ 玩家不在繩子上")
        
        print("-" * 30)
        
        # 測試繩子模板偵測
        ropes = bot.find_objects(bot.rope_templates, debug=True)
        print(f"偵測到 {len(ropes)} 條繩子:")
        for i, rope in enumerate(ropes):
            print(f"  {i+1}. {rope['name']} - 位置: {rope['position']} - 信心度: {rope['confidence']:.2f}")
        
        print("-" * 30)
        
        # 測試平台偵測
        monsters = bot.find_objects(bot.monster_templates, debug=True)
        print(f"偵測到 {len(monsters)} 隻怪物:")
        for monster in monsters:
            same_platform = bot.check_same_platform(monster['position'])
            platform_status = "同一平台" if same_platform else "不同平台"
            print(f"  怪物 {monster['name']} - {platform_status} - 位置: {monster['position']}")
        
        print("=" * 50)

    elif choice == '7':
        print("測試下繩子方法...")
        bot.test_climb_down_methods()

    elif choice == '8':
        print("詳細測試繩子偵測...")
        print("請輸入要測試的信心度閾值 (0.1-1.0，建議從 0.5 開始):")
        try:
            threshold = float(input("閾值: "))
            if 0.1 <= threshold <= 1.0:
                bot.test_rope_detection_with_threshold(threshold)
            else:
                print("閾值必須在 0.1 到 1.0 之間")
        except ValueError:
            print("無效的閾值，使用預設值 0.7")
            bot.test_rope_detection_with_threshold(0.7)

    elif choice == '9':
        print("配置下繩子策略...")
        print("=" * 50)
        print("選擇下繩子策略:")
        print("1. 僅使用按住下鍵（推薦，兼容性最好）")
        print("2. 智能嘗試多種方法（可能失敗，但覆蓋面廣）")
        print("3. 測試並選擇最佳方法")
        
        strategy_choice = input("請選擇策略 (1/2/3): ").strip()
        
        if strategy_choice == '1':
            print("✅ 已設定為僅使用按住下鍵方法")
            print("此方法兼容性最好，適合大部分楓之谷版本")
            bot.climb_down_strategy = 'simple'
            
        elif strategy_choice == '2':
            print("✅ 已設定為智能嘗試多種方法")
            print("將嘗試：按住下鍵 → 向左跳 → 向右跳")
            print("⚠️  注意：部分版本可能不支援同時按兩鍵")
            bot.climb_down_strategy = 'smart'
            
        elif strategy_choice == '3':
            print("即將測試所有下繩子方法...")
            successful_methods = bot.test_climb_down_methods()
            if successful_methods:
                print(f"\n推薦策略: 使用 {', '.join(successful_methods)} 方法")
                if 'down' in successful_methods:
                    print("建議：優先使用按住下鍵方法（兼容性最好）")
                    bot.climb_down_strategy = 'simple'
                elif len(successful_methods) > 1:
                    print("建議：使用智能策略嘗試多種方法")
                    bot.climb_down_strategy = 'smart'
                else:
                    bot.climb_down_strategy = 'simple'
            else:
                print("建議：默認使用按住下鍵方法")
                bot.climb_down_strategy = 'simple'
        else:
            print("無效選擇，保持預設策略")
        
        print("=" * 50)

    elif choice == '10':
        print("偵錯下繩子問題...")
        bot.debug_climb_down_test()

    elif choice == '11':
        print("即將開始自動練功...")
        bot.show_current_settings()
        print("請確保角色在安全位置（如繩子上或平台上）")
        print("最後倒數計時：")
        for i in range(5, 0, -1):
            print(f"  {i} 秒後開始自動練功...")
            time.sleep(1)
        print("開始自動練功！")
        bot.auto_training_loop()
    
    else:
        print("無效的選擇")
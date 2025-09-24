#ifndef CIMGUI_ESSENTIAL_H
#define CIMGUI_ESSENTIAL_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Forward declarations
typedef struct ImGuiContext ImGuiContext;
typedef struct ImGuiIO ImGuiIO;
typedef struct ImDrawData ImDrawData;
typedef struct ImVec2 ImVec2;
typedef struct ImVec4 ImVec4;

// Basic ImVec structures
struct ImVec2 {
    float x, y;
};

struct ImVec4 {
    float x, y, z, w;
};

// Window flags
enum ImGuiWindowFlags_ {
    ImGuiWindowFlags_None                   = 0,
    ImGuiWindowFlags_NoTitleBar             = 1 << 0,
    ImGuiWindowFlags_NoResize               = 1 << 1,
    ImGuiWindowFlags_NoMove                 = 1 << 2,
    ImGuiWindowFlags_NoScrollbar            = 1 << 3,
    ImGuiWindowFlags_NoScrollWithMouse      = 1 << 4,
    ImGuiWindowFlags_NoCollapse             = 1 << 5,
    ImGuiWindowFlags_AlwaysAutoResize       = 1 << 6,
    ImGuiWindowFlags_NoBackground           = 1 << 7,
    ImGuiWindowFlags_NoSavedSettings        = 1 << 8,
    ImGuiWindowFlags_NoMouseInputs          = 1 << 9,
    ImGuiWindowFlags_MenuBar                = 1 << 10,
    ImGuiWindowFlags_HorizontalScrollbar    = 1 << 11,
    ImGuiWindowFlags_NoFocusOnAppearing     = 1 << 12,
    ImGuiWindowFlags_NoBringToFrontOnFocus  = 1 << 13,
    ImGuiWindowFlags_AlwaysVerticalScrollbar= 1 << 14,
    ImGuiWindowFlags_AlwaysHorizontalScrollbar = 1 << 15,
    ImGuiWindowFlags_AlwaysUseWindowPadding = 1 << 16
};

// Core Context Functions
ImGuiContext* igCreateContext(void* shared_font_atlas);
void igDestroyContext(ImGuiContext* ctx);
ImGuiContext* igGetCurrentContext(void);
void igSetCurrentContext(ImGuiContext* ctx);

// IO Functions
ImGuiIO* igGetIO(void);
double igGetTime(void);
void igSetTime(double time);

// Frame Functions
void igNewFrame(void);
void igEndFrame(void);
void igRender(void);
ImDrawData* igGetDrawData(void);

// Window Functions
bool igBegin(const char* name, bool* p_open, int flags);
void igEnd(void);
bool igBeginChild(const char* str_id, struct ImVec2 size, bool border, int flags);
void igEndChild(void);

// Demo/Debug Windows
void igShowDemoWindow(bool* p_open);
void igShowMetricsWindow(bool* p_open);
void igShowAboutWindow(bool* p_open);

// Window Utilities
bool igIsWindowAppearing(void);
bool igIsWindowCollapsed(void);
bool igIsWindowFocused(int flags);
bool igIsWindowHovered(int flags);
void igGetWindowPos(struct ImVec2* pOut);
void igGetWindowSize(struct ImVec2* pOut);
float igGetWindowWidth(void);
float igGetWindowHeight(void);

// Window Manipulation
void igSetNextWindowPos(struct ImVec2 pos, int cond, struct ImVec2 pivot);
void igSetNextWindowSize(struct ImVec2 size, int cond);
void igSetNextWindowContentSize(struct ImVec2 size);
void igSetNextWindowCollapsed(bool collapsed, int cond);
void igSetNextWindowFocus(void);
void igSetNextWindowBgAlpha(float alpha);

// Layout
void igSeparator(void);
void igSameLine(float offset_from_start_x, float spacing);
void igNewLine(void);
void igSpacing(void);
void igDummy(struct ImVec2 size);
void igIndent(float indent_w);
void igUnindent(float indent_w);
void igBeginGroup(void);
void igEndGroup(void);
void igGetCursorPos(struct ImVec2* pOut);
float igGetCursorPosX(void);
float igGetCursorPosY(void);
void igSetCursorPos(struct ImVec2 local_pos);
void igSetCursorPosX(float local_x);
void igSetCursorPosY(float local_y);

// Text
void igText(const char* fmt);
void igTextColored(struct ImVec4 col, const char* fmt);
void igTextDisabled(const char* fmt);
void igTextWrapped(const char* fmt);
void igLabelText(const char* label, const char* fmt);
void igBulletText(const char* fmt);

// Main Widgets
bool igButton(const char* label, struct ImVec2 size);
bool igSmallButton(const char* label);
bool igInvisibleButton(const char* str_id, struct ImVec2 size, int flags);
bool igArrowButton(const char* str_id, int dir);
bool igCheckbox(const char* label, bool* v);
bool igRadioButton(const char* label, bool active);
void igProgressBar(float fraction, struct ImVec2 size_arg, const char* overlay);
void igBullet(void);

// Images
void igImage(void* user_texture_id, struct ImVec2 size, struct ImVec2 uv0, struct ImVec2 uv1, struct ImVec4 tint_col, struct ImVec4 border_col);
bool igImageButton(void* user_texture_id, struct ImVec2 size, struct ImVec2 uv0, struct ImVec2 uv1, int frame_padding, struct ImVec4 bg_col, struct ImVec4 tint_col);

// Combo Box
bool igBeginCombo(const char* label, const char* preview_value, int flags);
void igEndCombo(void);
bool igCombo(const char* label, int* current_item, const char* const items[], int items_count, int popup_max_height_in_items);

// Drag Sliders
bool igDragFloat(const char* label, float* v, float v_speed, float v_min, float v_max, const char* format, int flags);
bool igDragFloat2(const char* label, float v[2], float v_speed, float v_min, float v_max, const char* format, int flags);
bool igDragFloat3(const char* label, float v[3], float v_speed, float v_min, float v_max, const char* format, int flags);
bool igDragFloat4(const char* label, float v[4], float v_speed, float v_min, float v_max, const char* format, int flags);
bool igDragInt(const char* label, int* v, float v_speed, int v_min, int v_max, const char* format, int flags);

// Regular Sliders
bool igSliderFloat(const char* label, float* v, float v_min, float v_max, const char* format, int flags);
bool igSliderFloat2(const char* label, float v[2], float v_min, float v_max, const char* format, int flags);
bool igSliderFloat3(const char* label, float v[3], float v_min, float v_max, const char* format, int flags);
bool igSliderFloat4(const char* label, float v[4], float v_min, float v_max, const char* format, int flags);
bool igSliderInt(const char* label, int* v, int v_min, int v_max, const char* format, int flags);

// Input with Keyboard
bool igInputText(const char* label, char* buf, size_t buf_size, int flags, void* callback, void* user_data);
bool igInputTextMultiline(const char* label, char* buf, size_t buf_size, struct ImVec2 size, int flags, void* callback, void* user_data);
bool igInputFloat(const char* label, float* v, float step, float step_fast, const char* format, int flags);
bool igInputFloat2(const char* label, float v[2], const char* format, int flags);
bool igInputFloat3(const char* label, float v[3], const char* format, int flags);
bool igInputFloat4(const char* label, float v[4], const char* format, int flags);
bool igInputInt(const char* label, int* v, int step, int step_fast, int flags);

// Color Editors
bool igColorEdit3(const char* label, float col[3], int flags);
bool igColorEdit4(const char* label, float col[4], int flags);
bool igColorPicker3(const char* label, float col[3], int flags);
bool igColorPicker4(const char* label, float col[4], int flags, const float* ref_col);
bool igColorButton(const char* desc_id, struct ImVec4 col, int flags, struct ImVec2 size);

// Trees
bool igTreeNode(const char* label);
bool igTreeNodeEx(const char* label, int flags);
void igTreePush(const char* str_id);
void igTreePop(void);
float igGetTreeNodeToLabelSpacing(void);
bool igCollapsingHeader(const char* label, int flags);
bool igSelectable(const char* label, bool selected, int flags, struct ImVec2 size);

// List Boxes
bool igBeginListBox(const char* label, struct ImVec2 size);
void igEndListBox(void);
bool igListBox(const char* label, int* current_item, const char* const items[], int items_count, int height_in_items);

// Data Plotting
void igPlotLines(const char* label, const float* values, int values_count, int values_offset, const char* overlay_text, float scale_min, float scale_max, struct ImVec2 graph_size, int stride);
void igPlotHistogram(const char* label, const float* values, int values_count, int values_offset, const char* overlay_text, float scale_min, float scale_max, struct ImVec2 graph_size, int stride);

// Menus
bool igBeginMenuBar(void);
void igEndMenuBar(void);
bool igBeginMainMenuBar(void);
void igEndMainMenuBar(void);
bool igBeginMenu(const char* label, bool enabled);
void igEndMenu(void);
bool igMenuItem(const char* label, const char* shortcut, bool selected, bool enabled);

// Tooltips
void igBeginTooltip(void);
void igEndTooltip(void);
void igSetTooltip(const char* fmt);

// Popups
bool igBeginPopup(const char* str_id, int flags);
bool igBeginPopupModal(const char* name, bool* p_open, int flags);
void igEndPopup(void);
void igOpenPopup(const char* str_id, int popup_flags);
void igCloseCurrentPopup(void);

// Tables
bool igBeginTable(const char* str_id, int column, int flags, struct ImVec2 outer_size, float inner_width);
void igEndTable(void);
void igTableNextRow(int row_flags, float min_row_height);
bool igTableNextColumn(void);
bool igTableSetColumnIndex(int column_n);
void igTableSetupColumn(const char* label, int flags, float init_width_or_weight, unsigned int user_id);
void igTableSetupScrollFreeze(int cols, int rows);
void igTableHeadersRow(void);

// Tab Bars
bool igBeginTabBar(const char* str_id, int flags);
void igEndTabBar(void);
bool igBeginTabItem(const char* label, bool* p_open, int flags);
void igEndTabItem(void);
bool igTabItemButton(const char* label, int flags);
void igSetTabItemClosed(const char* tab_or_docked_window_label);

// Utilities
bool igIsItemHovered(int flags);
bool igIsItemActive(void);
bool igIsItemFocused(void);
bool igIsItemClicked(int mouse_button);
bool igIsItemVisible(void);
bool igIsItemEdited(void);
bool igIsItemActivated(void);
bool igIsItemDeactivated(void);
bool igIsAnyItemHovered(void);
bool igIsAnyItemActive(void);
bool igIsAnyItemFocused(void);
void igGetItemRectMin(struct ImVec2* pOut);
void igGetItemRectMax(struct ImVec2* pOut);
void igGetItemRectSize(struct ImVec2* pOut);
void igSetItemAllowOverlap(void);

// Miscellaneous Utilities
bool igIsKeyDown(int user_key_index);
bool igIsKeyPressed(int user_key_index, bool repeat);
bool igIsKeyReleased(int user_key_index);
bool igIsMouseDown(int button);
bool igIsMouseClicked(int button, bool repeat);
bool igIsMouseReleased(int button);
bool igIsMouseDoubleClicked(int button);
bool igIsMouseHoveringRect(struct ImVec2 r_min, struct ImVec2 r_max, bool clip);
void igGetMousePos(struct ImVec2* pOut);
void igGetMousePosOnOpeningCurrentPopup(struct ImVec2* pOut);
bool igIsMouseDragging(int button, float lock_threshold);
void igGetMouseDragDelta(struct ImVec2* pOut, int button, float lock_threshold);
void igResetMouseDragDelta(int button);

// Clipboard
const char* igGetClipboardText(void);
void igSetClipboardText(const char* text);

// Settings
void igLoadIniSettingsFromDisk(const char* ini_filename);
void igLoadIniSettingsFromMemory(const char* ini_data, size_t ini_size);
void igSaveIniSettingsToDisk(const char* ini_filename);
const char* igSaveIniSettingsToMemory(size_t* out_ini_size);

#ifdef __cplusplus
}
#endif

#endif // CIMGUI_ESSENTIAL_H
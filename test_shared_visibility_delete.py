import sys
import os

from models import db

def test_visibility_and_delete():
    print("==========================================================")
    print("TESTING GLOBAL VISIBILITY & OWNER-ONLY DELETE PERMISSIONS")
    print("==========================================================\n")

    student_a_id = "user_student_101"
    student_b_id = "user_student_202"
    staff_c_id   = "user_staff_303"

    # 1. Student A creates a Lost Item
    print("[1] Student A creates a Lost Item report...")
    item = db.add_item(
        creator_id=student_a_id,
        creator_name="Student A",
        creator_roll="STU-101",
        creator_phone="1234567890",
        item_name="Blue Noise-Cancelling Headphones",
        description="Left near quiet study room 302",
        filename=None,
        item_type="Lost",
        category="Electronics",
        location="Library 3rd Floor",
        date="2026-07-19",
        creator_email="studentA@campusfind.com"
    )
    item_id = item['id']
    print(f"    -> Item created successfully with ID: {item_id}\n")

    # 2. Student B posts a response to Student A's item
    print("[2] Student B posts a response to Student A's report...")
    db.add_response(
        item_id=item_id,
        responder_id=student_b_id,
        responder_name="Student B",
        responder_role="student",
        responder_roll="STU-202",
        responder_phone="9876543210",
        message="I turned these in to the main desk librarian!"
    )
    print("    -> Response recorded successfully.\n")

    # 3. VERIFY GLOBAL VISIBILITY
    print("[3] Testing Global Item & Response Visibility across accounts:")

    # Student A view
    item_view_a = db.get_item_by_id(item_id, current_user_id=student_a_id)
    print(f"    -> Student A (Owner) sees item: '{item_view_a['title']}' | Visible responses: {len(item_view_a['responses'])}")

    # Student B view
    item_view_b = db.get_item_by_id(item_id, current_user_id=student_b_id)
    print(f"    -> Student B (Responder) sees item: '{item_view_b['title']}' | Visible responses: {len(item_view_b['responses'])}")

    # Staff C view
    item_view_c = db.get_item_by_id(item_id, current_user_id=staff_c_id)
    print(f"    -> Staff C (Third Party) sees item: '{item_view_c['title']}' | Visible responses: {len(item_view_c['responses'])}")

    assert len(item_view_a['responses']) == 1, "Student A should see the response"
    assert len(item_view_b['responses']) == 1, "Student B should see the response"
    assert len(item_view_c['responses']) == 1, "Staff C should see the response"
    print("    => PASS: Every user sees all items and responses in the global feed!\n")

    # 4. VERIFY DELETE PERMISSIONS (UNAUTHORIZED ATTEMPTS)
    print("[4] Testing Delete Permissions (Unauthorized attempts):")

    # Student B attempts to delete Student A's item
    res_b = db.delete_item(item_id, current_user_id=student_b_id)
    print(f"    -> Student B attempts delete: Result = {res_b} (Permission Denied)")
    assert res_b is False, "Student B must NOT be allowed to delete Student A's item"

    # Staff C attempts to delete Student A's item
    res_c = db.delete_item(item_id, current_user_id=staff_c_id)
    print(f"    -> Staff C attempts delete: Result = {res_c} (Permission Denied)")
    assert res_c is False, "Staff C must NOT be allowed to delete Student A's item"

    # Verify item still exists in database
    check_item = db.get_item_by_id(item_id)
    assert check_item is not None, "Item must remain in DB after unauthorized delete attempts"
    print("    => PASS: Non-owners cannot delete posts!\n")

    # 5. VERIFY DELETE PERMISSIONS (AUTHORIZED OWNER DELETE)
    print("[5] Testing Delete Permissions (Authorized Owner delete):")
    res_a = db.delete_item(item_id, current_user_id=student_a_id)
    print(f"    -> Student A (Owner) attempts delete: Result = {res_a} (Success)")
    assert res_a is True, "Student A (Owner) should be allowed to delete their own item"

    # Verify item is removed from database for everyone
    deleted_check = db.get_item_by_id(item_id)
    assert deleted_check is None, "Item must be permanently deleted from DB"
    print("    => PASS: Post successfully deleted by owner!\n")

    print("==========================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! GLOBAL SHARED FEED IS ACTIVE.")
    print("==========================================================")

if __name__ == '__main__':
    test_visibility_and_delete()

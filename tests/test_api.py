"""
Tests for the Mergington High School API endpoints.
"""
import pytest


class TestRootEndpoint:
    """Tests for the root endpoint."""
    
    def test_root_redirects_to_static(self, client):
        """Test that root path redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the GET /activities endpoint."""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # We have 9 activities in the database
        
        # Verify some expected activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Basketball Team" in data
    
    def test_activities_have_correct_structure(self, client):
        """Test that each activity has the correct structure."""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)
            assert isinstance(activity["max_participants"], int)


class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint."""
    
    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity."""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Signed up newstudent@mergington.edu for Chess Club"
        
        # Verify the student was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist."""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_signup_duplicate_email(self, client):
        """Test that signing up twice with the same email fails."""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        assert response2.json()["detail"] == "Student already signed up for this activity"
    
    def test_signup_when_activity_full(self, client):
        """Test that signup fails when activity is at max capacity."""
        # Chess Club has max_participants of 12 and currently has 2 participants
        # Fill it up to max capacity
        for i in range(10):
            response = client.post(
                "/activities/Chess Club/signup",
                params={"email": f"student{i}@mergington.edu"}
            )
            assert response.status_code == 200
        
        # Try to add one more (should fail)
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "overflow@mergington.edu"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Activity is full"
    
    def test_signup_preserves_existing_participants(self, client):
        """Test that signing up doesn't remove existing participants."""
        # Get initial participants
        activities_before = client.get("/activities").json()
        initial_participants = activities_before["Programming Class"]["participants"].copy()
        
        # Add a new student
        response = client.post(
            "/activities/Programming Class/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        
        # Verify all previous participants are still there
        activities_after = client.get("/activities").json()
        current_participants = activities_after["Programming Class"]["participants"]
        
        for participant in initial_participants:
            assert participant in current_participants
        
        assert "newstudent@mergington.edu" in current_participants


class TestUnregisterEndpoint:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint."""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity."""
        # First, signup a student
        signup_response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": "temporary@mergington.edu"}
        )
        assert signup_response.status_code == 200
        
        # Now unregister
        response = client.delete(
            "/activities/Basketball Team/unregister",
            params={"email": "temporary@mergington.edu"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Unregistered temporary@mergington.edu from Basketball Team"
        
        # Verify the student was removed
        activities = client.get("/activities").json()
        assert "temporary@mergington.edu" not in activities["Basketball Team"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistration from an activity that doesn't exist."""
        response = client.delete(
            "/activities/Nonexistent Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_unregister_when_not_registered(self, client):
        """Test unregistration when student is not registered."""
        response = client.delete(
            "/activities/Drama Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student not registered for this activity"
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant."""
        # Unregister michael who is already in Chess Club
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        
        # Verify michael was removed
        activities = client.get("/activities").json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
        
        # Verify daniel is still there
        assert "daniel@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_after_unregister(self, client):
        """Test that a student can sign up again after unregistering."""
        email = "rejoining@mergington.edu"
        
        # Signup
        response1 = client.post(
            "/activities/Swimming Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Unregister
        response2 = client.delete(
            "/activities/Swimming Club/unregister",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Signup again should work
        response3 = client.post(
            "/activities/Swimming Club/signup",
            params={"email": email}
        )
        assert response3.status_code == 200
        
        # Verify the student is in the list
        activities = client.get("/activities").json()
        assert email in activities["Swimming Club"]["participants"]


class TestIntegration:
    """Integration tests for complex workflows."""
    
    def test_multiple_signups_for_same_student(self, client):
        """Test that a student can sign up for multiple activities."""
        email = "multitasker@mergington.edu"
        
        # Sign up for multiple activities
        activities_to_join = ["Chess Club", "Programming Class", "Art Studio"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify the student is in all activities
        all_activities = client.get("/activities").json()
        
        for activity in activities_to_join:
            assert email in all_activities[activity]["participants"]
    
    def test_activity_capacity_management(self, client):
        """Test that activity capacity is properly managed."""
        # Get Gym Class which has max 30 participants and currently has 2
        activities = client.get("/activities").json()
        gym_class = activities["Gym Class"]
        
        initial_count = len(gym_class["participants"])
        max_participants = gym_class["max_participants"]
        spots_available = max_participants - initial_count
        
        # Fill up the remaining spots
        for i in range(spots_available):
            response = client.post(
                "/activities/Gym Class/signup",
                params={"email": f"gymstudent{i}@mergington.edu"}
            )
            assert response.status_code == 200
        
        # Verify it's full
        activities = client.get("/activities").json()
        assert len(activities["Gym Class"]["participants"]) == max_participants
        
        # Try to add one more (should fail)
        response = client.post(
            "/activities/Gym Class/signup",
            params={"email": "overflow@mergington.edu"}
        )
        assert response.status_code == 400

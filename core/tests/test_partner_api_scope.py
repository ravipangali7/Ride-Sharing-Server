"""Partner / customer row-level scope for generic CRUD."""

from django.test import TestCase

from core import models
from core.views.admin.resource_scope import object_visible, scope_queryset


class ResourceScopeQuerysetTests(TestCase):
    def setUp(self):
        self.user_a = models.User.objects.create_user(
            phone="9811111111",
            password="pass12345",
            full_name="User A",
        )
        self.user_b = models.User.objects.create_user(
            phone="9822222222",
            password="pass12345",
            full_name="User B",
        )

    def test_vendors_scoped_to_owner_or_approved(self):
        va = models.Vendor.objects.create(
            user=self.user_a,
            store_name="Store A",
            store_logo="x/a.png",
            store_banner="x/ab.png",
            description="d",
            address="addr",
            latitude=27.7,
            longitude=85.3,
            registration_doc="x/r.pdf",
            delivery_charge=50,
            is_approved=False,
        )
        vb = models.Vendor.objects.create(
            user=self.user_b,
            store_name="Store B",
            store_logo="x/b.png",
            store_banner="x/bb.png",
            description="d",
            address="addr",
            latitude=27.7,
            longitude=85.3,
            registration_doc="x/r2.pdf",
            delivery_charge=50,
            is_approved=True,
        )
        qs = models.Vendor.objects.all()
        scoped_a = scope_queryset("vendors", qs, self.user_a)
        self.assertIn(va, scoped_a)
        self.assertNotIn(vb, scoped_a)
        scoped_b = scope_queryset("vendors", qs, self.user_b)
        self.assertIn(vb, scoped_b)
        # Approved vendor visible to others for shopping
        self.assertIn(vb, scoped_a)

    def test_restaurants_scoped_owner_or_approved(self):
        ra = models.Restaurant.objects.create(
            owner=self.user_a,
            name="R A",
            description="d",
            logo="x/l.png",
            cover_photo="x/c.png",
            address="a",
            latitude=27.7,
            longitude=85.3,
            phone="9800000000",
            delivery_radius_km=5,
            is_approved=False,
        )
        rb = models.Restaurant.objects.create(
            owner=self.user_b,
            name="R B",
            description="d",
            logo="x/l2.png",
            cover_photo="x/c2.png",
            address="a",
            latitude=27.7,
            longitude=85.3,
            phone="9800000001",
            delivery_radius_km=5,
            is_approved=True,
        )
        qs = models.Restaurant.objects.all()
        scoped_a = scope_queryset("restaurants", qs, self.user_a)
        self.assertIn(ra, scoped_a)
        self.assertIn(rb, scoped_a)

    def test_room_listings_owner_or_public(self):
        owner_prof = models.RoomOwnerProfile.objects.create(
            user=self.user_a,
            full_name="Owner A",
            phone="9811111111",
            citizenship_photo="x/c.png",
        )
        listing = models.RoomListing.objects.create(
            owner=owner_prof,
            title="Room",
            description="d",
            full_address="a",
            latitude=27.7,
            longitude=85.3,
            city="Ktm",
            area="A",
            room_type="single",
            bedrooms=1,
            bathrooms=1,
            monthly_rent=10000,
            is_furnished=False,
            has_parking=False,
            has_wifi=True,
            has_water=True,
            has_electricity=True,
            allowed_gender="any",
            is_available=True,
            is_approved=True,
            service_charge_type="percentage",
            service_charge_value=0,
        )
        qs = models.RoomListing.objects.all()
        scoped_b = scope_queryset("room_listings", qs, self.user_b)
        self.assertIn(listing, scoped_b)
        scoped_a = scope_queryset("room_listings", qs, self.user_a)
        self.assertIn(listing, scoped_a)

    def test_object_visible_vendor(self):
        v = models.Vendor.objects.create(
            user=self.user_a,
            store_name="S",
            store_logo="x/l.png",
            store_banner="x/b.png",
            description="d",
            address="a",
            latitude=1,
            longitude=1,
            registration_doc="x/r.pdf",
            delivery_charge=1,
            is_approved=False,
        )
        self.assertTrue(object_visible("vendors", v, self.user_a))
        self.assertFalse(object_visible("vendors", v, self.user_b))

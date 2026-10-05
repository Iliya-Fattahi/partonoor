"""
Real Django tests for the products app — including the explicit
"no online payment/cart" architectural guarantee from spec sections 17/69.
EXECUTION STATUS: written, not run in this sandbox (see
apps/projects/tests.py header for why). Run with:
    python manage.py test apps.products
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import ProductOrder, Product

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_test_image(name="p.png"):
    return SimpleUploadedFile(name, TINY_PNG, content_type="image/png")


class ProductViewTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            title="ریسه نوری پرتو نور", short_description="s", full_description="f",
            main_image=make_test_image(), published=True,
        )

    def test_list_returns_200(self):
        self.assertEqual(self.client.get(reverse("products:list")).status_code, 200)

    def test_detail_returns_200_for_published(self):
        self.assertEqual(self.client.get(self.product.get_absolute_url()).status_code, 200)

    def test_detail_returns_404_for_unpublished(self):
        self.product.published = False
        self.product.save()
        self.assertEqual(self.client.get(self.product.get_absolute_url()).status_code, 404)

    def test_order_cta_present_on_detail_page(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, self.product.order_cta_label)


class ProductModelHasNoPaymentFieldsTests(TestCase):
    """
    Architectural regression guard: this project must NEVER grow price,
    cart, or payment-gateway fields on Product (spec sections 17/69).
    A future contributor adding one of these fields "to be helpful" is
    exactly the kind of silent scope-creep this test exists to catch.
    """

    FORBIDDEN_FIELD_NAME_FRAGMENTS = [
        "price", "cost", "amount", "cart", "checkout", "payment",
        "gateway", "zarinpal", "transaction", "invoice",
    ]

    def test_no_forbidden_field_names_on_product(self):
        field_names = [f.name.lower() for f in Product._meta.get_fields()]
        for fragment in self.FORBIDDEN_FIELD_NAME_FRAGMENTS:
            matches = [name for name in field_names if fragment in name]
            self.assertEqual(
                matches, [],
                f"Product model must not have payment/cart-related fields, found: {matches}",
            )


class ProductOrderFlowTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.product = Product.objects.create(
            title="ریسه", slug="risheh", main_image=make_test_image("p.png"),
            short_description="x", full_description="x", published=True)
        self.url = self.product.get_absolute_url()
        self.payload = {"name": "علی رضایی", "phone": "۰۹۱۲۱۱۱۲۲۲۲", "city": "اهواز", "quantity": "۲۰۰ متر"}

    def test_valid_order_is_saved_and_redirects_back_to_the_order_section(self):
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].endswith("#order"))
        order = ProductOrder.objects.get()
        self.assertEqual(order.status, "new")
        self.assertEqual(order.product, self.product)

    def test_invalid_phone_is_rejected_with_persian_error(self):
        response = self.client.post(self.url, {**self.payload, "phone": "12"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProductOrder.objects.count(), 0)
        self.assertContains(response, "شماره تماس معتبر")

    def test_honeypot_blocks_bots(self):
        self.client.post(self.url, {**self.payload, "website": "http://spam"})
        self.assertEqual(ProductOrder.objects.count(), 0)

    def test_rate_limit_after_five_orders_from_one_ip(self):
        for _ in range(7):
            self.client.post(self.url, self.payload)
        self.assertEqual(ProductOrder.objects.count(), 5)

    def test_order_visible_in_admin_and_status_editable(self):
        from django.contrib.auth import get_user_model
        admin = get_user_model().objects.create_superuser("boss", "b@x.ir", "pw12345!")
        self.client.post(self.url, self.payload)
        order = ProductOrder.objects.get()
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("admin:products_productorder_changelist")).status_code, 200)
        change = self.client.get(reverse("admin:products_productorder_change", args=[order.pk]))
        self.assertContains(change, "علی رضایی")

    def test_page_has_no_cart_or_payment(self):
        html = self.client.get(self.url).content.decode()
        for word in ("سبد خرید", "پرداخت آنلاین", "checkout"):
            self.assertNotIn(word, html.replace("پرداخت آنلاین وجود ندارد", ""))

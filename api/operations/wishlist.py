import logging

from api.models import Stock, Wishlist as WishlistModel

logger = logging.getLogger(__name__)


class Wishlist:
    def toggle_wishlist(self, user, stock_id):
        stock = self._get_stock_by_id(stock_id)

        if stock is None:
            return {
                "status": False,
                "message": "Stock not found.",
                "data": None,
                "http_status": 404,
            }

        existing_item = self._get_wishlist_item(user=user, stock=stock)

        if existing_item is not None:
            deleted = self._delete_wishlist_item(existing_item)

            if not deleted:
                return {
                    "status": False,
                    "message": "Failed to remove wishlist item.",
                    "data": None,
                    "http_status": 500,
                }

            return {
                "status": True,
                "message": "Removed from wishlist.",
                "data": {
                    "stock_id": stock.id,
                    "is_wishlisted": False,
                },
                "http_status": 200,
            }

        created_item = self._create_wishlist_item(user=user, stock=stock)

        if created_item is None:
            return {
                "status": False,
                "message": "Failed to add wishlist item.",
                "data": None,
                "http_status": 500,
            }

        return {
            "status": True,
            "message": "Added to wishlist.",
            "data": {
                "stock_id": stock.id,
                "is_wishlisted": True,
            },
            "http_status": 200,
        }

    # ***************
    # *   Private   *
    # ***************
    def _get_stock_by_id(self, stock_id):
        return Stock.objects.filter(id=stock_id).first()

    def _get_wishlist_item(self, user, stock):
        return WishlistModel.objects.filter(user=user, stock=stock).first()

    def _create_wishlist_item(self, user, stock):
        try:
            return WishlistModel.objects.create(user=user, stock=stock)
        except Exception:
            logger.exception(
                "Failed to create wishlist item. user_id=%s, stock_id=%s",
                getattr(user, "id", None),
                getattr(stock, "id", None),
            )
            return None

    def _delete_wishlist_item(self, wishlist_item):
        try:
            wishlist_item.delete()
            return True
        except Exception:
            logger.exception(
                "Failed to delete wishlist item. wishlist_item_id=%s",
                getattr(wishlist_item, "id", None),
            )
            return False

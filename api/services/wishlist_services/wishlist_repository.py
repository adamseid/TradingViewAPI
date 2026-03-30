from api.models import Stock, Wishlist
import logging

logger = logging.getLogger(__name__)


class WishlistRepository:
    def get_stock_by_id(self, stock_id):
        return Stock.objects.filter(id=stock_id).first()

    def get_wishlist_item(self, user, stock):
        return Wishlist.objects.filter(user=user, stock=stock).first()

    def create_wishlist_item(self, user, stock):
        try:
            item = Wishlist.objects.create(user=user, stock=stock)
            return item
        except Exception:
            logger.exception(
                "Failed to create wishlist item. user_id=%s, stock_id=%s",
                getattr(user, "id", None),
                getattr(stock, "id", None),
            )
            return None

    def delete_wishlist_item(self, wishlist_item):
        try:
            wishlist_item.delete()
            return True
        except Exception:
            logger.exception(
                "Failed to delete wishlist item. wishlist_item_id=%s",
                getattr(wishlist_item, "id", None),
            )
            return False
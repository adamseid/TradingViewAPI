from api.services.wishlist_services.wishlist_repository import WishlistRepository


class WishlistService:
    def __init__(self, repository=None):
        self.repository = repository or WishlistRepository()

    def _service_response(self, status, message, data=None, http_status=None):
        return {
            "status": status,
            "message": message,
            "data": data,
            "http_status": http_status or (200 if status else 500),
        }

    def toggle_wishlist(self, user, stock_id):
        stock = self.repository.get_stock_by_id(stock_id)

        if stock is None:
            return self._service_response(
                status=False,
                message="Stock not found.",
                data=None,
                http_status=404,
            )

        existing_item = self.repository.get_wishlist_item(user=user, stock=stock)

        if existing_item is not None:
            deleted = self.repository.delete_wishlist_item(existing_item)

            if not deleted:
                return self._service_response(
                    status=False,
                    message="Failed to remove wishlist item.",
                    data=None,
                    http_status=500,
                )

            return self._service_response(
                status=True,
                message="Removed from wishlist.",
                data={
                    "stock_id": stock.id,
                    "is_wishlisted": False,
                },
                http_status=200,
            )

        created_item = self.repository.create_wishlist_item(user=user, stock=stock)

        if created_item is None:
            return self._service_response(
                status=False,
                message="Failed to add wishlist item.",
                data=None,
                http_status=500,
            )

        return self._service_response(
            status=True,
            message="Added to wishlist.",
            data={
                "stock_id": stock.id,
                "is_wishlisted": True,
            },
            http_status=200,
        )
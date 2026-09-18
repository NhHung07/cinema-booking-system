class ApplicationError(Exception):
    """Base error shared by domain and application use cases."""


class UserAlreadyExistsError(ApplicationError):
    pass


class InvalidCredentialsError(ApplicationError):
    pass


class MovieNotFoundError(ApplicationError):
    pass


class ShowtimeNotFoundError(ApplicationError):
    pass


class SeatNotFoundError(ApplicationError):
    pass


class SeatDoesNotBelongToRoomError(ApplicationError):
    pass


class BookingNotFoundError(ApplicationError):
    pass


class SeatAlreadyBookedError(ApplicationError):
    pass


class UnauthorizedBookingAccessError(ApplicationError):
    pass


class InvalidBookingError(ApplicationError):
    pass


class InvalidTokenError(ApplicationError):
    pass

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Text , UniqueConstraint, Time ,Date, Float
from datetime import time ,date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Trip(Base):
    __tablename__ = "trips"

    __table_args__ = (
        CheckConstraint(
            "travellers >= 1",
            name="check_travellers_positive",
        ),
        CheckConstraint(
            "days >= 1",
            name="check_days_positive",
        ),
        CheckConstraint(
            "budget_of_a_person > 0",
            name="check_budget_positive",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    city: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    travellers: Mapped[int] = mapped_column(
        nullable=False,
    )

    budget_of_a_person: Mapped[int] = mapped_column(
        nullable=False,
    )

    days: Mapped[int] = mapped_column(
        nullable=False,
    )

    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    preferences: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    origin: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    transport_preference: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Trip belongs to one user
    user: Mapped[User | None ]=relationship(
        back_populates="trips",
    )

    # Trip has many itinerary days
    itinerary_days: Mapped[list["ItineraryDay"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    
class ItineraryDay(Base):
    __tablename__ = "itinerary_days"

    __table_args__ = (
        UniqueConstraint(
            "trip_id",
            "day_number",
            name="unique_trip_day",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id"),
        nullable=False,
    )

    day_number: Mapped[int] = mapped_column(
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    trip: Mapped[Trip] = relationship(
        back_populates="itinerary_days",
    )

    activities: Mapped[list[Activity]] = relationship(
        back_populates="itinerary_day",
        cascade="all, delete-orphan",
    )
    
    
class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    itinerary_day_id: Mapped[UUID] = mapped_column(
        ForeignKey("itinerary_days.id"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    itinerary_day: Mapped["ItineraryDay"] = relationship(
        back_populates="activities"
    )
    
    location: Mapped[str] = mapped_column(
        Text,nullable=False,
    )
    
    activity_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="other",
    )

    place_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    
    estimated_cost: Mapped[int]=mapped_column(nullable=False,default=0,)
    
    notes:Mapped[str | None ] = mapped_column(
        Text,nullable=True,
    )
    start_time : Mapped[time | None] = mapped_column(Time,nullable=True,)
    end_time : Mapped[time | None] = mapped_column(Time,nullable=True,)
    
    
    
    
class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    email: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    trips: Mapped[list[Trip]] = relationship(back_populates="user",)
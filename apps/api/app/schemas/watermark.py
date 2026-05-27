from pydantic import BaseModel, Field


class WatermarkRegion(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @property
    def clamped(self) -> "WatermarkRegion":
        x = min(max(self.x, 0), 0.98)
        y = min(max(self.y, 0), 0.98)
        width = min(max(self.width, 0.01), 1 - x)
        height = min(max(self.height, 0.01), 1 - y)
        return WatermarkRegion(x=x, y=y, width=width, height=height)


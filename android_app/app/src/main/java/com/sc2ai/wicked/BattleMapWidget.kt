package com.sc2ai.wicked.battlemap

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import kotlin.math.abs

data class Point(val x: Float, val y: Float) {
    operator fun minus(other: Point) = Point(x - other.x, y - other.y)
    operator fun plus(other: Point) = Point(x + other.x, y - other.y)
}

data class Unit(
    val id: Int,
    var position: Point,
    val type: UnitType,
    val health: Float,
    val maxHealth: Float
)

enum class UnitType {
    DRONE, ZERGLING, ROACH, HYDRALISK, MUTALISK, OVERLORD, QUEEN,
    ULTRALISK, BROOD_LORD, CORRUPTOR, VIPER, INFESTOR,
    ENEMY_ZERG, ENEMY_TERRAN, ENEMY_PROTOSS
}

class BattleMapWidget @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {
    
    private val units = mutableListOf<Unit>()
    private val moveCommands = mutableListOf<Pair<Point, Point>>()
    private val attackPaths = mutableListOf<Pair<Point, Point>>()
    
    private var scale = 1f
    private var offsetX = 0f
    private var offsetY = 0f
    
    private var onUnitSelected: ((Unit?) -> Unit)? = null
    private var onMapTapped: ((Point) -> Unit)? = null
    
    private val terrainPaint = Paint().apply {
        color = Color.rgb(34, 85, 34)
        style = Paint.Style.FILL
    }
    
    private val gridPaint = Paint().apply {
        color = Color.rgb(50, 100, 50)
        style = Paint.Style.STROKE
        strokeWidth = 1f
    }
    
    private val unitPaints = mapOf(
        UnitType.DRONE to Paint().apply { color = Color.rgb(138, 138, 66) },
        UnitType.ZERGLING to Paint().apply { color = Color.rgb(200, 150, 100) },
        UnitType.ROACH to Paint().apply { color = Color.rgb(120, 80, 60) },
        UnitType.HYDRALISK to Paint().apply { color = Color.rgb(60, 100, 160) },
        UnitType.MUTALISK to Paint().apply { color = Color.rgb(160, 60, 180) },
        UnitType.ULTRALISK to Paint().apply { color = Color.rgb(80, 60, 40) },
        UnitType.ENEMY_ZERG to Paint().apply { color = Color.rgb(180, 50, 50) },
        UnitType.ENEMY_TERRAN to Paint().apply { color = Color.rgb(50, 50, 180) },
        UnitType.ENEMY_PROTOSS to Paint().apply { color = Color.rgb(180, 180, 50) }
    )
    
    private val healthPaint = Paint().apply {
        color = Color.GREEN
        style = Paint.Style.FILL
    }
    
    private val healthBgPaint = Paint().apply {
        color = Color.DKGRAY
        style = Paint.Style.FILL
    }
    
    private val moveLinePaint = Paint().apply {
        color = Color.CYAN
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }
    
    private val attackLinePaint = Paint().apply {
        color = Color.RED
        style = Paint.Style.STROKE
        strokeWidth = 2f
        pathEffect = android.graphics.DashPathEffect(floatArrayOf(10f, 5f), 0f)
    }
    
    private val selectionPaint = Paint().apply {
        color = Color.YELLOW
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }
    
    private var selectedUnit: Unit? = null
    
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        
        canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), terrainPaint)
        
        val gridSize = 32f * scale
        var x = offsetX % gridSize
        while (x < width) {
            canvas.drawLine(x, 0f, x, height.toFloat(), gridPaint)
            x += gridSize
        }
        var y = offsetY % gridSize
        while (y < height) {
            canvas.drawLine(0f, y, width.toFloat(), y, gridPaint)
            y += gridSize
        }
        
        for (command in moveCommands) {
            canvas.drawLine(
                command.first.x * scale + offsetX,
                command.first.y * scale + offsetY,
                command.second.x * scale + offsetX,
                command.second.y * scale + offsetY,
                moveLinePaint
            )
        }
        
        for (attack in attackPaths) {
            canvas.drawLine(
                attack.first.x * scale + offsetX,
                attack.first.y * scale + offsetY,
                attack.second.x * scale + offsetX,
                attack.second.y * scale + offsetY,
                attackLinePaint
            )
        }
        
        for (unit in units) {
            drawUnit(canvas, unit)
        }
        
        selectedUnit?.let { unit ->
            val radius = getUnitRadius(unit) * scale + 5
            canvas.drawCircle(
                unit.position.x * scale + offsetX,
                unit.position.y * scale + offsetY,
                radius,
                selectionPaint
            )
        }
    }
    
    private fun drawUnit(canvas: Canvas, unit: Unit) {
        val x = unit.position.x * scale + offsetX
        val y = unit.position.y * scale + offsetY
        val radius = getUnitRadius(unit) * scale
        
        val paint = unitPaints[unit.type] ?: Paint().apply { color = Color.WHITE }
        canvas.drawCircle(x, y, radius, paint)
        
        val healthWidth = radius * 2
        val healthHeight = 4f
        val healthY = y - radius - 8f
        
        canvas.drawRect(
            x - healthWidth / 2,
            healthY,
            x + healthWidth / 2,
            healthY + healthHeight,
            healthBgPaint
        )
        
        val healthPercent = unit.health / unit.maxHealth
        healthPaint.color = when {
            healthPercent > 0.6f -> Color.GREEN
            healthPercent > 0.3f -> Color.YELLOW
            else -> Color.RED
        }
        canvas.drawRect(
            x - healthWidth / 2,
            healthY,
            x - healthWidth / 2 + healthWidth * healthPercent,
            healthY + healthHeight,
            healthPaint
        )
    }
    
    private fun getUnitRadius(unit: Unit): Float {
        return when (unit.type) {
            UnitType.DRONE, UnitType.ZERGLING -> 6f
            UnitType.ROACH, UnitType.HYDRALISK -> 8f
            UnitType.MUTALISK -> 7f
            UnitType.ULTRALISK -> 12f
            else -> 8f
        }
    }
    
    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.action) {
            MotionEvent.ACTION_DOWN -> {
                val tapPoint = screenToMap(event.x, event.y)
                val tappedUnit = findUnitAt(tapPoint)
                selectedUnit = tappedUnit
                onUnitSelected?.invoke(tappedUnit)
                invalidate()
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                if (event.pointerCount == 1) {
                    offsetX += event.x - (selectedUnit?.position?.x ?: event.x)
                    offsetY += event.y - (selectedUnit?.position?.y ?: event.y)
                    invalidate()
                } else if (event.pointerCount == 2) {
                    val dx = event.getX(0) - event.getX(1)
                    val dy = event.getY(0) - event.getY(1)
                    val distance = kotlin.math.sqrt(dx * dx + dy * dy)
                    scale = (distance / 200f).coerceIn(0.5f, 5f)
                    invalidate()
                }
                return true
            }
        }
        return super.onTouchEvent(event)
    }
    
    private fun screenToMap(screenX: Float, screenY: Float): Point {
        return Point((screenX - offsetX) / scale, (screenY - offsetY) / scale)
    }
    
    private fun findUnitAt(point: Point): Unit? {
        val threshold = 20f / scale
        return units.find { u ->
            abs(u.position.x - point.x) < threshold && 
            abs(u.position.y - point.y) < threshold
        }
    }
    
    fun addUnit(unit: Unit) {
        units.add(unit)
        invalidate()
    }
    
    fun removeUnit(unitId: Int) {
        units.removeAll { it.id == unitId }
        invalidate()
    }
    
    fun updateUnitPosition(unitId: Int, newPosition: Point) {
        units.find { it.id == unitId }?.position = newPosition
        invalidate()
    }
    
    fun clearUnits() {
        units.clear()
        moveCommands.clear()
        attackPaths.clear()
        invalidate()
    }
    
    fun setOnUnitSelectedListener(listener: (Unit?) -> Unit) {
        onUnitSelected = listener
    }
    
    fun setOnMapTappedListener(listener: (Point) -> Unit) {
        onMapTapped = listener
    }
    
    fun commandMove(unitIds: List<Int>, target: Point) {
        for (id in unitIds) {
            units.find { it.id == id }?.let { unit ->
                moveCommands.add(Pair(unit.position, target))
                unit.position = target
            }
        }
        invalidate()
    }
    
    fun commandAttack(unitId: Int, target: Point) {
        units.find { it.id == unitId }?.let { unit ->
            attackPaths.add(Pair(unit.position, target))
        }
        invalidate()
    }
    
    fun zoomIn() {
        scale = (scale * 1.2f).coerceAtMost(5f)
        invalidate()
    }
    
    fun zoomOut() {
        scale = (scale / 1.2f).coerceAtLeast(0.5f)
        invalidate()
    }
    
    fun centerOn(x: Float, y: Float) {
        offsetX = width / 2f - x * scale
        offsetY = height / 2f - y * scale
        invalidate()
    }
}

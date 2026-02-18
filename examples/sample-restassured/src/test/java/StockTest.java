import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

public class StockTest extends BaseTest {

    @Test
    public void getStock_byWarehouse_returnsItems() {
        given()
            .spec(operatorSpec)
            .queryParam("warehouseId", 1)
        .when()
            .get("/stock")
        .then()
            .statusCode(200)
            .body("items", hasSize(greaterThan(0)))
            .body("items[0].productId", notNullValue())
            .body("items[0].quantity", greaterThan(0));
    }

    @Test
    public void getStock_byCategory_filtersCorrectly() {
        given()
            .spec(operatorSpec)
            .queryParam("warehouseId", 1)
            .queryParam("category", "DAIRY")
        .when()
            .get("/stock")
        .then()
            .statusCode(200)
            .body("items", hasSize(greaterThan(0)))
            .body("items[0].category", equalTo("DAIRY"));
    }

    @Test
    public void getStock_emptyWarehouse_returnsEmptyList() {
        given()
            .spec(operatorSpec)
            .queryParam("warehouseId", 999)
        .when()
            .get("/stock")
        .then()
            .statusCode(200)
            .body("items", hasSize(0));
    }

    @Test
    public void getStockItem_byProductId() {
        given()
            .spec(operatorSpec)
        .when()
            .get("/stock/{productId}", 100)
        .then()
            .statusCode(200)
            .body("productId", equalTo(100))
            .body("totalQuantity", greaterThanOrEqualTo(0))
            .body("warehouses", notNullValue());
    }

    @Test
    public void getStock_withLowStockFilter() {
        given()
            .spec(managerSpec)
            .queryParam("warehouseId", 1)
            .queryParam("belowThreshold", 10)
        .when()
            .get("/stock")
        .then()
            .statusCode(200)
            .body("items.quantity", everyItem(lessThan(10)));
    }
}

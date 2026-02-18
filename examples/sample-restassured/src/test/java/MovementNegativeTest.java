import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

public class MovementNegativeTest extends BaseTest {

    @Test
    public void createMovement_negativeQuantity_returns400() {
        given()
            .spec(operatorSpec)
            .body("{\"warehouseFromId\": 1, \"warehouseToId\": 2, " +
                  "\"productId\": 100, \"quantity\": -1, \"type\": \"TRANSFER\"}")
        .when()
            .post("/movements")
        .then()
            .statusCode(400)
            .body("error", equalTo("VALIDATION_ERROR"))
            .body("details.quantity", containsString("must be greater than 0"));
    }

    @Test
    public void createMovement_emptyBody_returns400() {
        given()
            .spec(operatorSpec)
            .body("{}")
        .when()
            .post("/movements")
        .then()
            .statusCode(400)
            .body("error", equalTo("VALIDATION_ERROR"));
    }

    @Test
    public void createMovement_noAuth_returns401() {
        given()
            .spec(baseSpec)
            .body("{\"warehouseFromId\": 1, \"warehouseToId\": 2, " +
                  "\"productId\": 100, \"quantity\": 5, \"type\": \"TRANSFER\"}")
        .when()
            .post("/movements")
        .then()
            .statusCode(401);
    }

    @Test
    public void getMovement_notFound_returns404() {
        given()
            .spec(operatorSpec)
        .when()
            .get("/movements/{id}", "nonexistent-id-99999")
        .then()
            .statusCode(404)
            .body("error", equalTo("NOT_FOUND"));
    }

    @Test
    public void createMovement_zeroQuantity_returns400() {
        given()
            .spec(operatorSpec)
            .body("{\"warehouseFromId\": 1, \"warehouseToId\": 2, " +
                  "\"productId\": 100, \"quantity\": 0, \"type\": \"TRANSFER\"}")
        .when()
            .post("/movements")
        .then()
            .statusCode(400);
    }

    @Test
    public void createMovement_sameWarehouse_returns422() {
        given()
            .spec(operatorSpec)
            .body("{\"warehouseFromId\": 1, \"warehouseToId\": 1, " +
                  "\"productId\": 100, \"quantity\": 10, \"type\": \"TRANSFER\"}")
        .when()
            .post("/movements")
        .then()
            .statusCode(422)
            .body("error", equalTo("BUSINESS_ERROR"))
            .body("message", containsString("same warehouse"));
    }
}

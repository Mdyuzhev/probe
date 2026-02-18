import io.restassured.response.Response;
import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

public class MovementCreateTest extends BaseTest {

    @Test
    public void createMovement_success_returns201() {
        given()
            .spec(operatorSpec)
            .body("{\"warehouseFromId\": 1, \"warehouseToId\": 2, " +
                  "\"productId\": 100, \"quantity\": 50, \"type\": \"TRANSFER\"}")
        .when()
            .post("/movements")
        .then()
            .statusCode(201)
            .body("status", equalTo("CREATED"))
            .body("id", notNullValue())
            .body("quantity", equalTo(50));
    }

    @Test
    public void createMovement_returnsLocationHeader() {
        given()
            .spec(operatorSpec)
            .body("{\"warehouseFromId\": 1, \"warehouseToId\": 3, " +
                  "\"productId\": 101, \"quantity\": 10, \"type\": \"TRANSFER\"}")
        .when()
            .post("/movements")
        .then()
            .statusCode(201)
            .header("Location", containsString("/api/v1/movements/"));
    }

    @Test
    public void createWriteOff_success() {
        given()
            .spec(managerSpec)
            .body("{\"warehouseFromId\": 1, \"productId\": 200, " +
                  "\"quantity\": 5, \"type\": \"WRITE_OFF\", \"reason\": \"damaged\"}")
        .when()
            .post("/movements")
        .then()
            .statusCode(201)
            .body("type", equalTo("WRITE_OFF"))
            .body("status", equalTo("CREATED"));
    }

    @Test
    public void createMovement_extractId() {
        String movementId = given()
            .spec(operatorSpec)
            .body("{\"warehouseFromId\": 1, \"warehouseToId\": 2, " +
                  "\"productId\": 300, \"quantity\": 1, \"type\": \"TRANSFER\"}")
        .when()
            .post("/movements")
        .then()
            .statusCode(201)
            .extract().path("id");

        given()
            .spec(operatorSpec)
        .when()
            .get("/movements/{id}", movementId)
        .then()
            .statusCode(200)
            .body("id", equalTo(movementId));
    }
}

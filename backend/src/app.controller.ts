import { Body, Controller, Post } from '@nestjs/common';
import {
  ApiBody,
  ApiConsumes,
  ApiOperation,
  ApiResponse,
} from '@nestjs/swagger';
import { AppService } from './app.service';
import { TextInputDto } from './dto/textInput.dto';

@Controller('api')
export class AppController {
  constructor(private readonly appService: AppService) {}

  // @Get()
  // getHello(): string {
  //   return this.appService.getHello();
  // }

  @Post('echo')
  @ApiOperation({ summary: '返回使用者輸入的文字' })
  @ApiConsumes('application/json')
  @ApiBody({
    type: TextInputDto,
    description: '要回傳的文字內容',
    examples: {
      example: {
        value: { text: '這是一個測試文字' },
        summary: '基本文字輸入示例',
      },
    },
  })
  @ApiResponse({
    status: 200,
    description: '成功回傳文字',
    schema: {
      type: 'object',
      properties: {
        message: { type: 'string' },
      },
    },
  })
  echoText(@Body() body: TextInputDto): { message: string } {
    return { message: body.text };
  }
}
